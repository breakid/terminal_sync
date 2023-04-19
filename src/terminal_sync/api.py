"""A REST API server for logging terminal commands to GhostWriter"""

# Standard Libraries
import logging
import sys
from asyncio.exceptions import TimeoutError
from datetime import datetime
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

try:
    # Get config settings from defaults, config file, and environment variables
    config = Config()

    # Create a GhostWriter client using config settings
    gw_client = GhostWriterClient(
        url=config.gw_url,
        oplog_id=config.gw_oplog_id,
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
    uuid: str = ""
    gw_id: int | None = None
    start_time: datetime = datetime.utcnow()
    end_time: datetime = datetime.utcnow()
    source_host: str | None = None
    description: str | None = None
    operator: str | None = config.operator
    output: str | None = None
    comments: str | None = None


# Dictionary used to store a mapping of UUIDs to log entries
# This allows terminal_sync to lookup and updated previous log entries when the command completes
log_entries: dict[str, Entry] = {}


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

            if entry.gw_id is None:
                entry.gw_id = await gw_client.create_log(entry)

                if entry.gw_id:
                    return (entry, f"[+] Logged to GhostWriter with ID: {entry.gw_id}")
            elif await gw_client.update_log(entry) is not None:
                return (entry, f"[+] Updated GhostWriter log: {entry.gw_id}")

            raise Exception("Unknown error")

        except TimeoutError:
            error_msg = f"A timeout occured while trying to connect to Ghostwriter at {config.gw_url}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=error_msg)
        except TransportQueryError as e:
            error_msg = f"Error encountered while fetching GraphQL schema: {e}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
        except GraphQLError as e:
            error_msg = f"Error with GraphQL query: {e}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
        except Exception as e:
            error_msg = f"An error occurred while trying to log to GhostWriter: {e}"
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

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
    global log_entries

    logger.debug(f"POST /commands/: {msg}")

    entry: Entry
    response: str

    entry, response = await log_command(msg)

    # Save the entry so we can update it when the command completes
    log_entries[msg.uuid] = entry

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
    if log_entries.get(msg.uuid):
        del log_entries[msg.uuid]

    return response


def run(host: str = config.termsync_listen_host, port: int = config.termsync_listen_port):
    """Run the API server using uvicorn

    Args:
        host (str, optional): The host address where the server will bind. Defaults to config.termsync_listen_host.
        port (int, optional): The port where the server will bind. Defaults to config.termsync_listen_port.
    """
    # Note: Imported here rather than at the top because it is optional
    # Third-party Libraries
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
