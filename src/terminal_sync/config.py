"""Defines a Config object used to store application settings"""

# Standard Libraries
import logging
import os
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from json import loads
from pathlib import Path
from typing import Any
from typing import Generator

# Third-party Libraries
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Defines a Config object used to store application settings

    Default settings passed into the constructor will be overridden by values loaded from specified config
    files, and the resulting values will be overridden by any matching environment variables.

    To prevent runtime errors caused for invalid config file or environment variable values, type checking if performed.
    The final type of each setting is checked against the type of the setting provided in the default dictionary or
    command-line arguments (e.g., from argparse).
    """

    gw_api_key_graphql: str = ""
    gw_api_key_rest: str = ""
    gw_description_token: str = "#desc"
    gw_oplog_id: int = 0
    gw_url: str = ""
    operator: str | None = None
    termsync_config: Path = Path("config.yaml")
    termsync_listen_host: str = "0.0.0.0"
    termsync_listen_port: int = 8000
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
                for setting_name, value in (yaml.safe_load(in_file) or {}).items():
                    if hasattr(self, setting_name):
                        setattr(self, setting_name, value)
                    else:
                        raise Exception(f"{setting_name} is not a supported setting")
        else:
            logger.warning(f"Unable to load config from file; {config_filepath} does not exist")

        # Override settings with any matching environment variables
        for setting_name, value in self:
            setting_name = setting_name.upper()

            if new_value := os.getenv(setting_name):
                # If the setting is a list or dictionary, parse the environment variable as a JSON object
                if isinstance(value, list | dict):
                    new_value = loads(new_value)

                setattr(self, setting_name, new_value)

        if not self.gw_api_key_graphql and not self.gw_api_key_rest:
            raise Exception("No GhostWriter API key specified")

        if self.gw_description_token not in self.termsync_keywords:
            self.termsync_keywords.append(self.gw_description_token)

    def __iter__(self) -> Generator:
        """Iterate through the object's attributes

        Yields:
            A tuple containing an attribute name and its value
        """
        yield from asdict(self).items()
