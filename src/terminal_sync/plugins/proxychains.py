# Standard Libraries
from logging import getLogger
from shlex import split

# Internal Libraries
from terminal_sync.log_entry import Entry

logger = getLogger(__name__)

# Note: Strings intentionally end with a space to prevent logging things like "vim /etc/proxychains.conf"
trigger_tokens: list[str] = ["proxychains ", "proxychains4 "]


def get_tool_from_proxychains(command: str) -> str | None:
    """Parse tool name from command

    Args:
        command (str): The command that was executed

    Returns:
        The tool name or None
    """
    i = 0

    try:
        # Use shlex.split rather than command.split(" ") in order to properly handle paths with spaces
        phrases = split(command)

        # Loop through phrases in the command until we find proxychains
        # Note: Use index rather than for-each to allow skipping the arguments for an option
        while i < len(phrases):
            if "proxychains" in phrases[i]:
                # Advance to next phrase
                i += 1
                break

            i += 1

        # Skip any proxychains options
        while i < len(phrases) and phrases[i].startswith("-"):
            if phrases[i] == "-q":
                i += 1
            elif phrases[i] == "-f":
                i += 2
            else:
                raise Exception(f"Invalid or unsupported proxychains argument: {phrases[i]}")

        # If there are any phrases left, return the first one as the command name
        if i < len(phrases):
            return phrases[i]

    except Exception as e:
        logger.exception(e)

    return None


def match(command: str) -> bool:
    """Return True if any of the trigger tokens appear in the command

    Args:
        command (str):

    Returns:
        Whether any of the trigger tokens appear in the command
    """
    return any(token in command for token in trigger_tokens)


def process(entry: Entry) -> Entry | None:
    """Parse the tool name from the command if any of the trigger tokens are appear in the command

    Args:
        entry (Entry): An Entry object containing a command string

    Returns:
        An Entry object with the tool name populated or None if the command does not contain any of the trigger tokens
    """
    if not match(entry.command):
        return None

    # Attempt to parse tool name from proxychains command
    tool_name: str | None = get_tool_from_proxychains(entry.command)

    # If no tool appears after the 'proxychains' string, it's an invalid command; don't log it
    if not tool_name:
        return None

    # Update the entry with the parsed tool name
    entry.tool = tool_name

    return entry
