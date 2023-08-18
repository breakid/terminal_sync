"""Defines a Config object used to store application settings"""

# Standard Libraries
from logging import getLogger
from os import getenv
from pathlib import Path
from re import IGNORECASE
from re import Pattern
from re import compile
from sys import exit
from typing import Any
from typing import Type

logger = getLogger(__name__)

# Define a regular expression used to validate the Ghostwriter URL
# Source: https://github.com/django/django/blob/6726d750979a7c29e0dd866b4ea367eef7c8a420/django/core/validators.py#L45
url_pattern: Pattern = compile(
    r"^(?:http)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    IGNORECASE,
)


class Config:
    """Defines a Config object used to store application settings

    Default settings will be overridden by environment variables (i.e., upper-case setting name)

    Attributes:
        gw_api_key_graphql (str): A Ghostwriter GraphQL API key
        gw_api_key_rest (str): A Ghostwriter REST API key
        gw_dest_host (str): The target of the command
        gw_oplog_id (int): The ID number of the Ghostwriter Oplog where entries will be recorded
        gw_src_host (str): The host where the command execution originates
        gw_ssl_check (bool): Whether to verify the SSL certificate of the Ghostwriter server; defaults to True
        gw_timeout_seconds (int): The number of seconds the server will wait for a response from Ghostwriter; defaults to 5
        gw_url (str): The URL for your Ghostwriter instance
        operator (str): The name / identifier of the user creating the log entries
        termsync_desc_token (str): String used to delimit the command and an optional description; defaults to `#desc`
        termsync_enabled (bool): Whether terminal_sync logging is enabled; defaults to True
        termsync_json_log_dir (str): The directory where JSON log files are written; defaults to `logs`
        termsync_log_level (str): The logging level (valid options are: ERROR, WARN, INFO, DEBUG); defaults to INFO
        termsync_save_all_local (bool): Whether to save all logs using the JSON file (may have a performance impact);
            defaults to False
    """

    gw_api_key_graphql: str = ""
    gw_api_key_rest: str = ""
    gw_dest_host: str = ""
    gw_oplog_id: int = 0
    gw_src_host: str = ""
    gw_ssl_check: bool = True
    gw_timeout_seconds: int = 5
    gw_url: str = ""
    operator: str = ""
    termsync_desc_token: str = "#desc"
    termsync_enabled: bool = True
    termsync_json_log_dir: Path = Path("logs")
    termsync_log_level: str = "INFO"
    termsync_save_all_local: bool = False
    termsync_keywords: list[str] = []  # TODO: Temp

    def __init__(self):
        # Load environment variables from .env file
        try:
            # Note: Imported here rather than at the top to allow the dependency to be optional
            from dotenv import load_dotenv  # isort:skip

            load_dotenv()
        except ImportError:
            logger.warning('dotenv is not installed; skipping loading ".env"')

        setting_name: str
        new_value: Any
        setting_type: Type

        # Override defaults with environment variables
        for setting_name, setting_type in Config.__annotations__.items():  # self:
            logger.debug(f"Checking for environment variable: {setting_name.upper()}")

            if (new_value := getenv(setting_name.upper())) is not None:
                try:
                    # Convert the new value to the proper type
                    if setting_type is bool:
                        new_value = new_value.lower() in ("1", "true", "yes")
                    else:
                        new_value = setting_type(new_value)
                    setattr(self, setting_name, new_value)
                except ValueError:
                    logger.error(f"{setting_name.upper()} is not a valid {setting_type.__name__}")
                    exit(1)

        # TODO: Temp?
        if self.termsync_desc_token not in self.termsync_keywords:
            self.termsync_keywords.append(self.termsync_desc_token)

        # Create alias attributes for initializing Entry objects
        self.source_host: str = self.gw_src_host
        self.destination_host: str = self.gw_dest_host
        self.oplog_id: int = self.gw_oplog_id

        self._validate()

    def __iter__(self):
        """Iterate through the object's attributes

        Yields:
            A tuple containing an attribute name and its value
        """
        yield from self.__dict__.items()

    def _validate(self):
        valid_url: bool = url_pattern.match(self.gw_url) is not None

        if valid_url and self.gw_oplog_id > 0 and (self.gw_api_key_graphql or self.gw_api_key_rest):
            logger.debug("Ghostwriter logging enabled")
        else:
            if not valid_url:
                logger.warning("[-] Invalid Ghostwriter URL; activity will not be logged to Ghostwriter!")
            elif self.gw_oplog_id < 1:
                logger.error("[-] Oplog ID must be a positive integer")
            else:
                logger.warning("[-] No Ghostwriter API key specified; activity will not be logged to Ghostwriter!")

            # Cannot log to Ghostwriter without a URL or API key; enable local log storage as a backup
            self.termsync_save_all_local = True
            logger.info("[*] Local logging enabled as a fallback")

        if not self.termsync_desc_token.startswith("#"):
            logger.error("termsync_desc_token must start with a '#'")
            exit(1)
