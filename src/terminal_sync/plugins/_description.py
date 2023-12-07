# Standard Libraries
from logging import getLogger

# Internal Libraries
from terminal_sync import cfg as config
from terminal_sync.log_entry import Entry

logger = getLogger(__name__)


def process(entry: Entry) -> Entry | None:
    desc_token: str = config.termsync_desc_token

    # Extract the description from the command, if desc_token is present
    if entry.command and desc_token in entry.command:
        logger.debug("Parsing description from command")
        entry.command, entry.description = entry.command.split(desc_token)
        return entry

    return None
