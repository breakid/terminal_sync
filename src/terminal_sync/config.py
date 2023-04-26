"""Defines a Config object used to store application settings"""

# Standard Libraries
import logging
import os
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Generator

# Third-party Libraries
from yaml import safe_load

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Defines a Config object used to store application settings

    Default settings defined in this class will be overridden by values in the config file, and both will be overridden
    by any matching environment variables (i.e., upper-case setting name).

    Attributes:
        gw_api_key_graphql (str): A GhostWriter GraphQL API key
        gw_api_key_rest (str): A GhostWriter REST API key
        gw_description_token (str): String used to delimit the command and an optional description; defaults to `#desc`
        gw_oplog_id (int): The ID number of the GhostWriter Oplog where entries will be recorded
        gw_url (str): The URL for your GhostWriter instance
        operator (str): The name / identifier of the user creating the log entries
        termsync_config (Path): The path to the config file; defaults to `config.yaml`
        termsync_json_log_dir (str): The directory where JSON log files are written; defaults to `log_archive`
        termsync_keywords (list[str]): List of keywords that will trigger logging a command to GhostWriter
        termsync_listen_host (str): The host address where the server will bind
        termsync_listen_port (int): The host port where the server will bind
        termsync_save_all_local (bool): Whether to save all logs using the JSON file (may have a performance impact);
            defaults to False
        termsync_timeout_seconds (int): The number of seconds the server will wait for a response from GhostWriter
    """

    gw_api_key_graphql: str = ""
    gw_api_key_rest: str = ""
    gw_description_token: str = "#desc"
    gw_oplog_id: int = 0
    gw_url: str = ""
    operator: str | None = None
    termsync_config: Path = Path("config.yaml")
    termsync_json_log_dir: str = "log_archive"
    termsync_listen_host: str = "127.0.0.1"
    termsync_listen_port: int = 8000
    termsync_save_all_local: bool = False
    termsync_timeout_seconds: int = 10

    # TODO: Automatically add keywords "exported" by registered command parsers
    # TODO: This list should only contain keywords that don't have an associated command parser
    termsync_keywords: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Override default settings with values from the config file or environment variables"""
        setting_name: str
        value: Any
        new_value: Any

        # Load environment variables from .env file
        try:
            # Note: Imported here rather than at the top because it is optional
            from dotenv import load_dotenv  # isort:skip

            load_dotenv()
        except ImportError:
            logger.warning('dotenv is not installed; skipping loading ".env"')

        # Override the default config filepath using an environment variable, if it exists
        config_filepath: Path = Path(os.getenv("TERMSYNC_CONFIG") or self.termsync_config)

        # Load settings from config file, if it exists
        if config_filepath.exists():
            logger.info(f"Logging config from: {config_filepath}")

            with open(config_filepath) as in_file:
                for setting_name, value in (safe_load(in_file) or {}).items():
                    if hasattr(self, setting_name):
                        setattr(self, setting_name, value)
                    else:
                        raise Exception(f"{setting_name} is not a supported setting")
        else:
            logger.warning(f"Unable to load config from file; {config_filepath} does not exist")

        # Override settings with any matching environment variables
        for setting_name, value in self:
            if new_value := os.getenv(setting_name.upper()):
                # If an environment variable setting exists, parse the value as YAML in order to handle
                # lists, dictionaries, ints, booleans, etc.
                setattr(self, setting_name, safe_load(new_value))

        if not self.gw_api_key_graphql and not self.gw_api_key_rest:
            # Cannot log to GhostWriter without an API key; enable local log storage as a backup
            self.termsync_save_all_local = True
            logger.warning("No GhostWriter API key specified; activity will not be logged to GhostWriter!")
            logger.info("Local logging enabled as a fallback")

        if self.gw_oplog_id < 0:
            raise ValueError("Oplog ID must be a positive integer")

        if self.gw_description_token not in self.termsync_keywords:
            self.termsync_keywords.append(self.gw_description_token)

    def __iter__(self) -> Generator:
        """Iterate through the object's attributes

        Yields:
            A tuple containing an attribute name and its value
        """
        yield from asdict(self).items()
