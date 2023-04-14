# -*- coding: utf-8 -*-
"""Defines a Config object used to store application settings"""

# Standard Libraries
import logging
import os
from pathlib import Path
from typing import Any, Optional

# Third-party Libraries
import yaml


logger = logging.getLogger(__name__)


class Config:
    """Defines a Config object used to store application settings

    Default settings passed into the constructor will be overridden by values loaded from specified config
    files, and the resulting values will be overridden by any matching environment variables.

    To prevent runtime errors caused for invalid config file or environment variable values, type checking if performed.
    The final type of each setting is checked against the type of the setting provided in the default dictionary or command-line arguments (e.g., from argparse).
    """

    def __init__(
        self,
        defaults: dict[str, Any],
        config_filepaths: Optional[Path | list[Path]] = None,
        cli_args: dict[str, Any] = None,
    ) -> None:
        """Initialize the Config object

        Args:
            defaults (dict[str, Any]): A dictionary containing default values for all configuration settings
            config_filepaths (Optional[Path  |  list[Path]], optional): The path to a YAML config file or a list of
                such paths
            cli_args (dict[str, Any], optional): A dictionary of command-line arguments

        Raises:
            FileNotFoundError: If one of the specified config files does not exist
            YAMLError: If there was an error parsing a YAML config
        """
        # Ensure parameters are properly initialized
        config_filepaths = config_filepaths or []
        config_filepaths = config_filepaths if type(config_filepaths) == list else [config_filepaths]
        cli_args = {} if cli_args is None else cli_args

        # Initialize settings (to a copy of defaults so that the assert below will work properly)
        setting_name: str
        settings: dict[str, Any] = {} if defaults is None else dict(**defaults)

        # Merge the command-line arguments with the defaults before baselining types
        if cli_args:
            settings.update({arg: value for arg, value in cli_args.items() if value is not None})

        # Save the type of each setting and use it for type checking
        setting_types = {setting_name: type(value) for setting_name, value in settings.items()}

        # Load settings from config file, if specified
        # Supports multiple config files, with later configs overriding values in previous ones
        for filepath in config_filepaths:
            with open(filepath, "r") as in_file:
                settings.update(yaml.safe_load(in_file) or {})

        # Load environment variables from .env file
        try:
            # Note: Imported here rather than at the top because it is optional
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            logger.warning('dotenv is not installed; skipping loading ".env"')

        # Override settings with any matching environment variables
        settings.update({setting: os.getenv(setting.upper()) for setting in settings if os.getenv(setting.upper())})

        # Re-apply command-line args so they take precedence over everything else
        # NOTE: Be sure to use 'None' as the default value for CLI args or else this will always override your settings
        # with the defaults
        settings.update({arg: value for arg, value in cli_args.items() if value is not None})

        # Loop through the stored list of settings rather than self.__dict__ because the latter contains other things we don't want to check, like functions
        for setting_name, value in settings.items():
            # Assertion used to identify settings added to the config file but not given a default value
            assert (
                setting_name in defaults or setting_name in cli_args
            ), f"{setting_name} does not appear in default_settings or command-line parameters"

            # If a value begins with '%%', use the value of an existing setting
            if type(value) == str and value.startswith("%%"):
                settings[setting_name] = settings.get(value[2:])

            # Perform type checking
            if not isinstance(settings.get(setting_name), setting_types.get(setting_name)):
                raise TypeError(
                    f'"{setting_name}" has type {type(settings.get(setting_name))} rather than {setting_type}'
                )

        # Add settings to the config object itself (for convenience)
        for setting_name, value in settings.items():
            setattr(self, setting_name, value)

        # Save a list of the setting names, so we can easily loop through settings on the config object
        # without getting extraneous items like built-in functions
        self.settings: list[str] = sorted(settings.keys())

    def __iter__(self) -> tuple[str, str]:
        """Generator that iterates through the attributes of a Config object

        Yields:
            A tuple containing an attribute name and its value
        """
        for name in self.settings:
            yield name, getattr(self, name)

    def __repr__(self):
        """Return a JSON string of the Config object

        Returns:
            A JSON representation of the Config object
        """
        return str(dict(self)).replace("'", '"')

    def __str__(self):
        """Return a YAML string of the Config object

        Returns:
            A YAML representation of the Config object
        """
        return yaml.dump(dict(self))
