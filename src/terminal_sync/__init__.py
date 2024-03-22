"""Marks the current directory as a Python package"""

# Standard Libraries
import logging.config
from os import getenv
from os import makedirs
from sys import exit
from time import gmtime

# Third-party Libraries
from yaml import safe_load

# Internal Libraries
from terminal_sync.config import Config


# Note: Version is also defined in pyproject.toml. Ideally, to ensure they don't get out of sync, version would
# only be defined once; however, the project one is only accessible if terminal_sync is installed as a package
__version__ = "0.4.0"

# Initialize log directory to prevent logging configuration errors
makedirs(getenv("TERMSYNC_LOG_DIR", "logs"), exist_ok=True)

try:
    with open("logging_config.yaml", "r") as f:
        logging_config: dict = safe_load(f.read())
        logging.config.dictConfig(logging_config)
except ValueError as e:
    print(f"[terminal_sync] ERROR: {e}")
except FileNotFoundError as e:
    print(f"[terminal_sync] ERROR: {e}")


# Initialize config
cfg: Config = Config()


# Create a custom exception that prevents logging a command
class NoLogException(Exception):
    pass
