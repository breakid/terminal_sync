# Standard Libraries
import argparse
import asyncio
from datetime import datetime
from glob import glob
from json import dump
from json import load
from logging import getLogger
from os import makedirs
from os import remove
from sys import exit

# Third-party Libraries
from gql.transport.exceptions import TransportQueryError
from graphql.error.graphql_error import GraphQLError

# Internal Libraries
from terminal_sync.config import Config
from terminal_sync.ghostwriter import GhostWriterClient
from terminal_sync.log_entry import Entry

logger = getLogger(__name__)

config: Config = Config()


def get_entry(args: dict[str, datetime | str]) -> tuple[Entry, bool]:
    # CLI arguments appear last and will override config settings
    attrs: dict[str, bool | datetime | int | str] = dict(config, **args)

    # Initalize an Entry object from the CLI arguments and config options
    entry: Entry = Entry.from_dict(attrs)

    # Search for stored file by OpLod ID and command UUID
    files: list[str] = glob(f"{config.termsync_json_log_dir}/{entry.oplog_id}_*_{entry.uuid}.json")

    if len(files) == 0:
        return entry, True

    # Load the existing log data from disk and update it with the current entry
    with open(files[0]) as in_file:
        return Entry.from_dict(load(in_file)).update(attrs), False


def save_log(entry: Entry) -> None:
    """Save the entry to a JSON file

    By default, used to cache entries if they fail to log to GhostWriter but can be enabled for all logs

    Args:
        uuid (str): A universally unique identifier for the entry
        entry (Entry): The entry to be saved
    """
    logger.debug(f'Saving log with UUID "{entry.uuid}": {entry}')

    # Make sure the output directory exists
    makedirs(config.termsync_json_log_dir, exist_ok=True)

    # Write updated dictionary back to disk
    with open(config.termsync_json_log_dir / entry.json_filename(), "w") as out_file:
        dump(dict(entry), out_file)


async def log_command(entry: Entry, new_entry: bool = True) -> None:
    """Create and/or return a GhostWriter log entry object

    Checks whether the command in the specified message should trigger logging
    If so, return an existing entry or create a new entry if a matching one does not exist

    Args:
        entry (Message): A log entry object
    """
    logger.debug(f"Entry: {entry}")

    # TODO: Move this to a plugin
    # Parse the description from the command, if applicable
    if entry.command and config.termsync_desc_token in entry.command:
        entry.command, entry.description = entry.command.split(config.termsync_desc_token)

    # Flag used to determine whether the entry was logged successfully
    # If not, the 'finally' clause will save the log locally
    saved: bool = False

    try:
        # Initialize Ghostwriter client if URL and API key are specified
        # This allows terminal_sync to be used for local logging without a GhostWriter instance
        if config.gw_url and (config.gw_api_key_graphql or config.gw_api_key_rest):
            # Create a GhostWriter client using config settings
            gw_client: GhostWriterClient = GhostWriterClient(
                url=config.gw_url,
                graphql_api_key=config.gw_api_key_graphql,
                rest_api_key=config.gw_api_key_rest,
                timeout_seconds=config.gw_timeout_seconds,
            )

            gw_id: int | None = await gw_client.log(entry)

            if gw_id:
                saved = True
                entry.gw_id = gw_id

                if new_entry:
                    logger.info(f"[+] Logged to GhostWriter with ID: {entry.gw_id}")
                else:
                    logger.info(f"[+] Updated GhostWriter log: {entry.gw_id}")

    except TimeoutError:
        logger.exception(f"A timeout occurred while connecting to {config.gw_url}")
    except TransportQueryError as e:
        logger.exception(f"An error encountered while fetching the GraphQL schema: {e}")
    except GraphQLError as e:
        logger.exception(f"Error with GraphQL query: {e}")
    except Exception as e:
        logger.exception(e)
    finally:
        if config.termsync_save_all_local or not saved:
            logger.info(f"[+] Logged to JSON file with UUID: {entry.uuid}")
            save_log(entry)
        elif new_entry:
            # Save new entries so that they can be updated when the command completes
            save_log(entry)
        else:
            # Remove temp log file
            remove(config.termsync_json_log_dir / entry.json_filename())


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--comment", dest="comments", type=str, help="Additional information about the command")
    parser.add_argument("-i", "--id", dest="gw_id", type=str, help="The GhostWriter ID of a log entry to update")
    # Note: Do not set a default for start_time or end_time because we don't want to accidentally overwrite the original start_time in Ghostwriter
    parser.add_argument(
        "-s",
        "--start-time",
        dest="start_time",
        type=lambda s: datetime.strptime(s, "%F %T"),
        help="Timestamp when the command was executed",
    )
    parser.add_argument(
        "-e",
        "--end-time",
        dest="end_time",
        # action=lambda s: datetime.strptime(s, "%F %T"),
        type=datetime.fromisoformat,
        help="Timestamp when the command finished executing",
    )
    parser.add_argument(
        "--src-host",
        dest="source_host",
        type=str,
        help="The host where the command execution originates (from the defender's perspective; for example: an internal host running a SOCKS proxy)",
    )
    parser.add_argument("-d", "--dest-host", dest="destination_host", type=str, help="The host the command targets")
    parser.add_argument("-o", "--output", dest="output", type=str, help="The output of the command")
    parser.add_argument("-u", "--uuid", dest="uuid", type=str, help="A universally unique identifier for the command")
    parser.add_argument("command", nargs="?", type=str, help="The command to log (must be quoted)")
    return parser.parse_args()


def main():
    args: argparse.Namespace = parse_arguments()

    # Exit if no command is specified and no Ghostwriter log ID is specified
    if not args.command and not args.gw_id:
        # No command was run, so we don't need to print the "Executed" or "Completed" message
        exit(1)

    # Initalize an Entry object from data saved on disk, config options, and CLI arguments
    entry: Entry
    new_entry: bool
    entry, new_entry = get_entry(vars(args))

    # gw_id is only specified when a user updates a Ghostwriter log manually from command-line
    # If it isn't specified, a command was just run; display an "Executed" or "Completed" message
    if entry.gw_id:
        new_entry = False
    elif config.termsync_enabled:
        if new_entry:
            logger.info(f'[*] Executed: "{entry.command}" at {entry.start_time}')
        else:
            logger.info(f'[+] Completed: "{entry.command}" at {entry.end_time}')

    # Log the command if any trigger words appear or a Ghostwriter log entry ID was specified
    if args.gw_id or any(keyword in entry.command for keyword in config.termsync_keywords):
        asyncio.run(log_command(entry, new_entry))


if __name__ == "__main__":
    main()
