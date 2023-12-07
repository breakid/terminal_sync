# Standard Libraries
from logging import getLogger
from shlex import split

# Internal Libraries
from terminal_sync import NoLogException
from terminal_sync import cfg as config
from terminal_sync.log_entry import Entry


def process(entry: Entry) -> Entry | None:
    # Use shlex.split rather than entry.command.split(" ") in order to properly handle paths with spaces
    for token in split(entry.command):
        if token == config.termsync_nolog_token:
            raise NoLogException(__name__)

    return entry
