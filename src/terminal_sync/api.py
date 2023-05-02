"""A REST API server for logging terminal commands to GhostWriter"""

# Standard Libraries
import json
import logging
import sys
from asyncio.exceptions import TimeoutError
from datetime import datetime
from os import getenv
from os import makedirs
from pathlib import Path
from re import match
from time import gmtime

# Third-party Libraries
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from gql.transport.exceptions import TransportQueryError
from graphql.error.graphql_error import GraphQLError
from pydantic import BaseModel

# Internal Libraries
from terminal_sync.config import Config
from terminal_sync.export_csv import export_csv
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

gw_client: GhostWriterClient | None = None

try:
    # Get config settings from defaults, config file, and environment variables
    config = Config()

    # If no API key specified, skip creating the client
    # This allows terminal_sync to be used for local logging without a GhostWriter instance
    if config.gw_url and (config.gw_api_key_graphql or config.gw_api_key_rest):
        # Create a GhostWriter client using config settings
        gw_client = GhostWriterClient(
            url=config.gw_url,
            graphql_api_key=config.gw_api_key_graphql,
            rest_api_key=config.gw_api_key_rest,
            timeout_seconds=config.termsync_timeout_seconds,
        )
except Exception as e:
    logger.exception(e)
    sys.exit(1)


# =============================================================================
# ******                            API Server                            *****
# =============================================================================

app = FastAPI()


class Message(BaseModel):
    """Defines a Message class that encapsulates the log entry data passed from a client

    Used to force FastAPI to pass the data through the request body rather than as query parameters
    """

    command: str
    comments: str | None = None
    description: str | None = None
    gw_id: int | None = None
    operator: str | None = config.operator
    oplog_id: int = config.gw_oplog_id
    output: str | None = None
    source_host: str | None = getenv("SRC_HOST")
    start_time: datetime = datetime.utcnow()
    end_time: datetime = datetime.utcnow()
    uuid: str = ""


# Dictionary used to store a mapping of UUIDs to log entries
# This allows terminal_sync to lookup and updated previous log entries when the command completes
log_entries: dict[str, Entry] = {}


async def save_log(uuid: str, entry: Entry) -> None:
    """Save the entry to a JSON file

    By default, used to cache entries if they fail to log to GhostWriter but can be enabled for all logs

    Args:
        uuid (str): A universally unique identifier for the entry
        entry (Entry): The entry to be saved
    """
    logger.debug(f'Saving log with UUID "{uuid}": {entry}')

    # Make sure the output directory exists
    makedirs(config.termsync_json_log_dir, exist_ok=True)

    # Write updated dictionary back to disk
    with open(Path(config.termsync_json_log_dir) / entry.json_filename(), "w") as out_file:
        json.dump(entry.gw_fields(), out_file)


async def log_command(msg: Message) -> tuple[Entry, str]:
    """Create and/or return a GhostWriter log entry object

    Checks whether the command in the specified message should trigger logging
    If so, return an existing entry or create a new entry if a matching one does not exist

    Args:
        msg (Message): An object containing command information sent by a client

    Returns:
        tuple[Entry, str]: A tuple containing the entry with updated gw_id and a message to display to the user

    Raises:
        HTTPException: If the command didn't trigger logging or an error occurred while communicating with GhostWriter
    """
    error_msg: str

    # Check whether any of the keywords that trigger logging appear in the command
    if any(keyword in msg.command for keyword in config.termsync_keywords):
        # Flag used to determine whether the entry was logged successfully
        # If not, the 'finally' clause will save the log locally
        saved: bool = False

        try:
            # Parse the description from the command, if applicable
            if config.gw_description_token in msg.command:
                (msg.command, msg.description) = msg.command.split(config.gw_description_token)

            # Try to lookup an existing entry by UUID
            entry: Entry | None = log_entries.get(msg.uuid)

            if entry:
                # Update the existing entry using msg attributes
                entry.update(dict(msg))
            else:
                # Scenarios:
                #   - Creating a new log entry
                #   - Performing an out-of-band entry update (i.e., gw_id provided, UUID is None)
                entry = Entry.from_dict(dict(msg))

            # Tell static analyzers that `entry` is no longer None
            assert isinstance(entry, Entry)

            # If gw_client isn't initialized, return early and let the 'finally' clause save the log locally
            if gw_client is None:
                return (entry, f"[+] Logged to JSON file with UUID: {msg.uuid}")

            if entry.gw_id is None:
                # Save the entry so we can update it when the command completes
                # Note: If we don't save the entry here, it won't be saved at all if an exception occurs
                #       This can result in duplicate JSON objects being created for the same log
                #       Luckily, since we're saving a reference to an object, the gw_id of the saved entry will be
                #       updated as well, if the creation is successful
                log_entries[msg.uuid] = entry
                entry.gw_id = await gw_client.create_log(entry)

                if entry.gw_id:
                    saved = True
                    return (entry, f"[+] Logged to GhostWriter with ID: {entry.gw_id}")
            elif await gw_client.update_log(entry) is not None:
                saved = True
                return (entry, f"[+] Updated GhostWriter log: {entry.gw_id}")

            raise Exception("Unknown error")

        except TimeoutError:
            error_msg = f"A timeout occurred while connecting to {config.gw_url}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=error_msg)
        except TransportQueryError as e:
            logger.exception(f"Error encountered while fetching GraphQL schema: {e}")
            error_msg = e.errors[0].get("message")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
        except GraphQLError as e:
            error_msg = f"Error with GraphQL query: {e}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
        except Exception as e:
            error_msg = str(e)
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
        finally:
            if entry and (not saved or config.termsync_save_all_local):
                await save_log(msg.uuid, entry)

    # If the command doesn't trigger logging, return HTTP code 204
    raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/commands/")
async def pre_exec(msg: Message) -> str:
    """Create a new log entry; intended to be used by a pre-exec hook

    Args:
        msg (Message): A Message object containing information about the command executed / action taken

    Returns:
        str: The message to display to the user
    """
    logger.debug(f"POST /commands/: {msg}")

    entry: Entry
    response: str

    entry, response = await log_command(msg)

    return response


# Endpoint to update an existing command
@app.put("/commands/")
async def post_exec(msg: Message) -> str:
    """Endpoint to update an existing log entry

    Intended to be used by a post-exec hook.
    This will create a new log entry if not existing match is found. It's better to have a duplicate than no log at all.

    Args:
        msg (Message): A Message object containing information about the command executed / action taken

    Returns:
        str: The message to display to the user
    """
    global log_entries

    logger.debug(f"PUT /commands/: {msg}")

    # The command field from a bash session will include the start timestamp; split it from the command
    # Example msg.command: '2023-04-11 19:18:24 ps'
    if m := match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)", msg.command):
        (_, msg.command) = m.groups()

    entry: Entry
    response: str

    # Create or update the log entry
    entry, response = await log_command(msg)

    # Remove the entry from the buffer so the buffer doesn't get huge
    # Note: The removal is done here, rather than in log_command() in case no previous entry existed and the creation
    #       flow was followed
    if log_entries.get(msg.uuid):
        del log_entries[msg.uuid]

    return response


@app.on_event("shutdown")
async def app_shutdown() -> None:
    """Export a GhostWriter CSV file on server shutdown"""
    try:
        csv_filepath: Path = export_csv(Path(config.termsync_json_log_dir), Path(config.termsync_json_log_dir))
        logger.info(f"Exported cached logs to: {csv_filepath}")
    except Exception as e:
        logger.exception(e)


def run(host: str = config.termsync_listen_host, port: int = config.termsync_listen_port):
    """Run the API server using uvicorn

    Args:
        host (str, optional): The host address where the server will bind. Defaults to config.termsync_listen_host.
        port (int, optional): The port where the server will bind. Defaults to config.termsync_listen_port.
    """
    # Note: Imported here rather than at the top because it is optional
    import uvicorn  # isort:skip

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
