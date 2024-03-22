# Standard Libraries
import argparse
import asyncio
from datetime import datetime
from glob import glob
from importlib import import_module
from json import dump
from json import load
from logging import getLogger
from os import makedirs
from os import remove
from pathlib import Path
from sys import exit
from types import ModuleType

# Third-party Libraries
from gql.transport.exceptions import TransportQueryError
from graphql.error.graphql_error import GraphQLError

# Internal Libraries
from terminal_sync import __version__ as termsync_version
from terminal_sync import NoLogException
from terminal_sync import cfg as config
from terminal_sync.ghostwriter import GhostwriterClient
from terminal_sync.log_entry import Entry

logger = getLogger(__name__)


def load_plugins() -> dict[str, ModuleType]:
    """Dynamically load plugins

    This allows new command processors to be added without modifying the main code base

    Returns:
        dict[str, ModuleType]: A dictionary mapping module name to the module object
    """
    # Note: This function must be defined in a module directly in the package root directory;
    # otherwise, change this line
    package: Path = Path(__file__).parent
    plugin_dir: str = "plugins"
    modules: dict[str, ModuleType] = {}

    for module_path in (package / plugin_dir).glob("*.py"):
        module_name: str = module_path.stem

        # Skip files like __init__.py
        if module_name.startswith("__"):
            continue

        # Import and save a reference to the module
        modules[module_name] = import_module(f"{package.name}.{plugin_dir}.{module_name}")

    return modules


plugins: dict[str, ModuleType] = load_plugins()


def get_entry(args: dict[str, datetime | str]) -> tuple[Entry, bool]:
    """Initialize an Entry object using default config values, CLI arguments, and data stored on disk

    Later sources override values from previous ones (i.e., CLI overrides default config, stored data overrides CLI arguments)

    Args:
        args (dict[str, datetime  |  str]): The CLI arguments

    Returns:
        tuple[Entry, bool]: A tuple containing the initialize entry and a boolean indicating whether a previous entry existed
    """
    # CLI arguments appear last so that they override config settings (if they are set)
    attrs: dict[str, bool | datetime | int | str] = dict(config, **{key: value for key, value in args.items() if value})

    # Initalize an Entry object from the CLI arguments and config options
    entry: Entry = Entry.from_dict(attrs)

    # Search for stored file by OpLod ID and command UUID
    files: list[str] = [file for file in Path(config.termsync_cache_dir).glob(f"{entry.oplog_id}_*_{entry.uuid}.json")]

    if len(files) == 0:
        return entry, True

    # Load the existing log data from disk and update it with the current entry
    with open(files[0]) as in_file:
        return Entry.from_dict(load(in_file)).update(attrs), False


def save_log(entry: Entry) -> None:
    """Save the entry to a JSON file

    By default, used to cache entries if they fail to log to Ghostwriter but can be enabled for all logs

    Args:
        uuid (str): A universally unique identifier for the entry
        entry (Entry): The entry to be saved
    """
    logger.debug(f'Saving log with UUID "{entry.uuid}": {entry}')

    # Make sure the output directory exists
    makedirs(config.termsync_cache_dir, exist_ok=True)

    # Write updated dictionary back to disk
    with open(config.termsync_cache_dir / entry.json_filename(), "w") as out_file:
        dump(dict(entry), out_file)


async def log_command(entry: Entry, new_entry: bool = True) -> None:
    """Create and/or return a Ghostwriter log entry object

    Checks whether the command in the specified message should trigger logging
    If so, return an existing entry or create a new entry if a matching one does not exist

    Args:
        entry (Message): A log entry object
    """
    logger.debug(f"Entry: {entry}")

    # Flag used to determine whether the entry was logged successfully
    # If not, the 'finally' clause will save the log locally
    saved: bool = False

    try:
        # Initialize Ghostwriter client if URL and API key are specified
        # This allows terminal_sync to be used for local logging without a Ghostwriter instance
        if config.gw_url and (config.gw_api_key_graphql or config.gw_api_key_rest):
            # Create a Ghostwriter client using config settings
            gw_client: GhostwriterClient = GhostwriterClient(
                url=config.gw_url,
                graphql_api_key=config.gw_api_key_graphql,
                rest_api_key=config.gw_api_key_rest,
                user_agent=f"terminal_sync/{termsync_version}",
                timeout_seconds=config.gw_timeout_seconds,
                verify_ssl=config.gw_ssl_check,
            )

            gw_id: int | None = await gw_client.log(entry)

            if gw_id:
                saved = True
                entry.gw_id = gw_id

                if new_entry:
                    logger.info(f"[+] Logged to Ghostwriter with ID: {entry.gw_id}")
                else:
                    logger.info(f"[+] Updated Ghostwriter log: {entry.gw_id}")

    except TimeoutError:
        logger.exception(f"A timeout occurred while connecting to {config.gw_url}")
    except TransportQueryError as e:
        logger.exception(f"An error encountered while fetching the GraphQL schema: {e}")
    except GraphQLError as e:
        logger.exception(f"Error with GraphQL query: {e}")
    except Exception as e:
        if "Not found." in e.args:
            logger.error(f"[!] ERROR: Ghostwriter entry ID {entry.gw_id} not found")
        else:
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
            remove(config.termsync_cache_dir / entry.json_filename())


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments

    Returns:
        argparse.Namespace: Parsed CLI arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--comment", dest="comments", type=str, help="Additional information about the command")
    parser.add_argument("-d", "--description", dest="description", type=str, help="Description of the command")
    # TODO: Make this mutually exclusive with UUID? (this should only be used for manual updates and UUID should only be used for automatic logging)
    parser.add_argument("-i", "--id", dest="gw_id", type=str, help="The Ghostwriter ID of a log entry to update")
    # Note: Do not set a default for start_time or end_time because we don't want to accidentally overwrite the original start_time in Ghostwriter
    parser.add_argument(
        "-s",
        "--start-time",
        dest="start_time",
        type=datetime.fromisoformat,
        help="Timestamp when the command was executed",
    )
    parser.add_argument(
        "-e",
        "--end-time",
        dest="end_time",
        type=datetime.fromisoformat,
        help="Timestamp when the command finished executing",
    )
    parser.add_argument(
        "--src-host",
        dest="source_host",
        type=str,
        help="The host where the command execution originates (from the defender's perspective; for example: an internal host running a SOCKS proxy)",
    )
    parser.add_argument("--dest-host", dest="destination_host", type=str, help="The host the command targets")
    parser.add_argument("--operator", dest="operator", type=str, help="The operator who ran the command")
    parser.add_argument("-o", "--output", dest="output", type=str, help="The output of the command")
    parser.add_argument("-u", "--uuid", dest="uuid", type=str, help="A universally unique identifier for the command")
    parser.add_argument("command", nargs="?", type=str, help="The command to log (must be quoted)")
    return parser.parse_args()


def process_entry(entry: Entry) -> Entry | None:
    """Pass the entry to the 'process()' function of each loaded plugin

    Args:
        entry (Entry): A raw (initialized but unprocessed) Entry object

    Returns:
        Entry | None: A processed Entry object or 'None' if the entry should not be logged
    """
    # TODO: This is probably a better way to do this...
    new_entry: Entry | None = None

    try:
        # Pass the entry to the 'process()' function of each loaded plugin
        for plugin_name, plugin in plugins.items():
            # If new_entry is initialized, reset entry to match it; this allows plugins to stack (i.e., multiple plugins
            # can process the same command)
            entry = new_entry if new_entry is not None else entry

            # If the entry matches plugin processing criteria, the process() function will return a modified entry
            # If not, it will return None; we 'or' it with the existing new_entry to ensure a later non-matching plugin
            # doesn't erase changes from a previous one
            new_entry = plugin.process(entry) or new_entry
    except NoLogException as e:
        new_entry = None
        logger.debug(f"{e.message} raised a NoLogException")

    return new_entry


def run(args: dict[str, datetime | str]) -> None:
    command: str = args.get("command")
    gw_id: str = args.get("gw_id")

    # Return if the user explicitly stated not to log the command
    if config.termsync_nolog_token in command:
        return

    # Return if neither command nor Ghostwriter log ID are specified
    if not command and not gw_id:
        return

    entry: Entry
    new_entry: bool

    if gw_id:
        # gw_id is only specified when a user updates a Ghostwriter log manually from command-line
        # Construct an entry using only CLI args to avoid overwriting log entries with default terminal_sync values
        # TODO: Verify this doesn't actually overwrite log entry data (i.e., comments, and start and end time have defaults in Entry)
        entry = Entry(args)
        new_entry = False
    elif config.termsync_enabled:
        # Check whether terminal_sync is enabled here rather than above to allow use of the manual update functionality even if automatic logging is disabled

        # Initalize an Entry object from data saved on disk, config options, and CLI arguments
        entry, new_entry = get_entry(args)

        # If gw_id isn't specified, assume a command was just run and display either an "Executed" or "Completed" message
        if new_entry:
            logger.info(f'[*] Executed: "{entry.command}" at {entry.start_time}')
        else:
            logger.info(f'[+] Completed: "{entry.command}" at {entry.end_time}')

    if entry := process_entry(entry):
        asyncio.run(log_command(entry, new_entry))


# Note: Define main() to provide a single function with no arguments that can be called from __main__.py
def main():
    run(vars(parse_arguments()))


if __name__ == "__main__":
    main()
