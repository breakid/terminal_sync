"""Marks the current directory as a Python package"""

# Standard Libraries
import logging
from os import getenv
from time import gmtime

# Note: Version is also defined in pyproject.toml. Ideally, to ensure they don't get out of sync, version would
# only be defined once; however, the project one is only accessible if terminal_sync is installed as a package
__version__ = "0.4.0"

log_level: str = getenv("TERMSYNC_LOG_LEVEL", "INFO").upper()

# Create a handler that outputs to the console (stderr by default)
# Use `logging.StreamHandler(sys.stdout)` to output to stdout instead
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[terminal_sync] %(message)s"))

if log_level == "ERROR":
    console_handler.setLevel(logging.ERROR)
elif log_level == "WARN":
    console_handler.setLevel(logging.WARNING)
elif log_level == "DEBUG":
    console_handler.setLevel(logging.DEBUG)
else:
    console_handler.setLevel(logging.INFO)


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
