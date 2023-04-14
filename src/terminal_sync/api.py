# -*- coding: utf-8 -*-
"""A REST API server for logging terminal commands to GhostWriter"""

# Stardard Libraries
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from re import match
from time import gmtime
from typing import Optional

# Third-party Libraries
from fastapi import FastAPI
from pydantic import BaseModel

# Internal Libraries
from terminal_sync.config import Config
from terminal_sync.ghostwriter import GhostWriterClient
from terminal_sync.log_entry import Entry


# =============================================================================
# ******                             Logging                              *****
# =============================================================================

# Create a handler that outputs to the console (stderr by default)
# Use `logging.StreamHandler(sys.stdout)` to output to stdout instead
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s"))

# Create a file handler for detailed debug logs
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(funcName)s - %(message)s")
file_formatter.converter = gmtime  # Use UTC timestamps

file_handler = logging.FileHandler("terminal_sync.log")
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)

# Create a logger
logging.basicConfig(
    # Note: You must set the global logging level to the most inclusive setting you want to log; individual handlers
    # can limit the level but not increase it
    level=logging.NOTSET,
    handlers=[file_handler, console_handler],
)
logger = logging.getLogger("terminal_sync")


# =============================================================================
# ******                          Config Parsing                          *****
# =============================================================================

# Default configuration settings
default_settings: dict[str, bool | int | str] = {
    "gw_api_key_graphql": "",
    "gw_api_key_rest": "",
    "gw_description_token": "#desc",
    "gw_oplog_id": 0,
    "gw_url": "",
    "operator": "",
    # TODO: Automatically add keywords "exported" by registered command parsers; this list should only contain keywords that don't have an associated command parser
    "termsync_keywords": ["aws", "kubectl", "proxychains"],
    "termsync_listen_host": "0.0.0.0",
    "termsync_listen_port": 8000,
    "timeout_seconds": 10,
}

config = Config(default_settings, Path(__file__).with_name("config.yaml"))

# Explicitly add the description token to the list of keywords so that it triggers logging
config.termsync_keywords.append(config.gw_description_token)

# =============================================================================
# ******                        GhostWriter Client                        *****
# =============================================================================

# Assume we're using GraphQL unless its API key isn't specified and the REST API key is
api_key: str = config.gw_api_key_graphql
api_type: str = "graphql"

if not config.gw_api_key_graphql:
    if config.gw_api_key_rest:
        api_key = config.gw_api_key_rest
        api_type = "rest"
    else:
        logger.error("No GhostWriter API key specified")
        sys.exit(1)

gw_client = GhostWriterClient(
    url=config.gw_url,
    api_key=api_key,
    oplog_id=config.gw_oplog_id,
    api_type=api_type,
    timeout_seconds=config.timeout_seconds,
)

# =============================================================================
# ******                            API Server                            *****
# =============================================================================

app = FastAPI()


# Note: Create a Message class that inherits from BaseModel to force the data into the body rather than sending it
# as query parameters
class Message(BaseModel):
    command: str
    uuid: Optional[str] = None
    gw_id: Optional[int] = None
    start_time: str = datetime.utcnow().strftime("%F %H:%M:%S")
    end_time: str = datetime.utcnow().strftime("%F %H:%M:%S")
    description: Optional[str] = None
    output: Optional[str] = None
    comments: Optional[str] = None


# Dictionary used to store a mapping of UUIDs to log entries
# This allows terminal_sync to lookup and updated previous log entries when the command completes
log_entries: dict[str, Entry] = {}


async def log_command(msg: Message) -> Optional[Entry]:
    """Create and/or return a GhostWriter log entry object

    Checks whether the command in the specified message should trigger logging
    If so, return an existing entry or create a new entry if a matching one does not exist

    Args:
        msg (Message): An object containing command information sent by a client

    Returns:
        Optional[Entry]: An existing or newly created Entry object for the specified command
    """
    global log_entries

    # Check whether any of the keywords that trigger logging appear in the command
    if any(keyword in msg.command for keyword in config.termsync_keywords):
        # Save the UUID then remove it from the message so the msg can be used to create the Entry object
        uuid: str = msg.uuid
        del msg.uuid

        # Parse the description from the command, if applicable
        if config.gw_description_token in msg.command:
            (msg.command, msg.description) = msg.command.split(config.gw_description_token)

        # Try to lookup an existing entry by UUID
        entry: Entry = log_entries.get(uuid)

        if entry:
            # Update the existing entry using msg attributes
            entry.update(**vars(msg))

            # Entry updated; remove it from the buffer so the buffer doesn't get huge
            del log_entries[uuid]
        else:
            # Scenarios:
            #   - Creating a new log entry
            #   - Performing an out-of-band entry update (i.e., gw_id provided, UUID is None)
            entry = Entry(
                **vars(msg),
                source_host=os.getenv("SRC_HOST"),
                operator=config.operator,
            )

            # If creating a new log entry, UUID will be populated
            # Save the entry so we can update it when the command completes
            if uuid is not None:
                log_entries[uuid] = entry

        # Create or update the log entry
        entry = await gw_client.log(entry)

        return entry

    return None


@app.post("/commands/")
async def pre_exec(msg: Message):
    """Endpoint to create a new log entry

    Intended to be used by a pre-exec hook

    Args:
        msg (Message): A Message object containing information about the command executed / action taken

    Returns:
        Optional[Entry]: The successfully logged Entry object or None (indicates failure to log the entry)
    """

    logger.debug(f"POST /commands/: {msg}")

    try:
        return await log_command(msg)
    except Exception as e:
        return e


# Endpoint to update an existing command
@app.put("/commands/")
async def post_exec(msg: Message):
    """Endpoint to update an existing log entry

    Intended to be used by a post-exec hook.
    This will create a new log entry if not existing match is found. It's better to have a duplicate than no log at all.

    Args:
        msg (Message): A Message object containing information about the command executed / action taken

    Returns:
        Optional[Entry]: The successfully updated Entry object or None (indicates failure to create a missing entry)
    """
    logger.debug(f"PUT /commands/: {msg}")

    # The command field from a bash session will include the start timestamp; split it from the command
    # Example msg.command: '2023-04-11 19:18:24 ps'
    if m := match("(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)", msg.command):
        (msg.start_time, msg.command) = m.groups()

    # Create or update the log entry
    return await log_command(msg)

    # return {"gw_id": entry.gw_id}

    # entry: Entry = await log_command(msg)

    # # If no matching entry is found, create a new one (better to have a duplicate than no log at all)
    # if entry:
    #     return await create_entry(msg)

    # # Add the output to the retrieved entry
    # entry.set_output(msg.output)

    # result: dict = await gw_client.log(entry)

    # return await gw_client.log(entry)


# @app.on_event("startup")
# async def app_startup():
#     # TODO: Load saved commands from file or database
#     pass


# @app.on_event("shutdown")
# async def app_shutdown():
#     # TODO: Write list of saved commands to a file or database
#     pass


def run(host=config.termsync_listen_host, port=config.termsync_listen_port):
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
