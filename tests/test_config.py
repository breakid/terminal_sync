"""Test the Config class"""

# Standard Libraries
from os import getenv
from os import unsetenv
from pathlib import Path
from typing import Any
from typing import Generator

# Third-party Libraries
from pytest import raises

# Internal Libraries
from terminal_sync.config import Config


# Set via environment variables in pyproject.toml
config_attributes: dict[str, int | str] = {
    "gw_api_key_graphql": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwic3ViX25h8WUiOiJkYnJldWtpcm9uIiwic3ViX2vtYWlsIjoiIiwiYXVkIjoiR2hvc3R3cml0ZXIiLCJpYXQiOjE2OT62NTA3OTYuMzI0OTE2LCJleHAiOjE3MjYzNTk1ODN9._YJMUBb4noMLazmalZjE-mBZgqpIKsWv1jJi8VQ4K-c",
    "gw_api_key_rest": "qoWrhDIz.Mn5fkoxrqsFZZ2pSR13AgW88m9WFNmsk",
    "gw_dest_host": "192.168.1.100 (LAB-DC01)",
    "gw_oplog_id": 1,
    "gw_src_host": "192.168.1.2 (Ops VM)",
    "gw_ssl_check": False,
    "gw_timeout_seconds": 10,
    "gw_url": "https://ghostwriter.local",
    "operator": "neo",
    "termsync_desc_token": "#desc",
    "termsync_enabled": False,
    "termsync_json_log_dir": Path("json_logs"),
    "termsync_log_level": "DEBUG",
    "termsync_nolog_token": "#dontlog",
    "termsync_save_all_local": True,
    # Aliased attributes
    "source_host": "192.168.1.2 (Ops VM)",
    "destination_host": "192.168.1.100 (LAB-DC01)",
    "oplog_id": 1,
}


def test_config_init():
    """Test that the Config object is populated properly from environment variables"""

    # Unset an environment variable to ensure the config will properly handle the value being missins
    unsetenv("TERMSYNC_DESC_TOKEN")
    assert getenv("TERMSYNC_DESC_TOKEN") is None

    config: Config = Config()

    for attr, value in config_attributes.items():
        assert getattr(config, attr) == value, f"[config.{attr}] Expected: {value}; Actual: {getattr(config, attr)}"


def test_config_iter() -> None:
    """Verify the `__iter__()` function successfully loops through all attributes and returns the correct values"""
    gen: Generator = Config().__iter__()

    assert isinstance(gen, Generator)

    # Verify the correct values are returned
    for attr, value in config_attributes.items():
        print(f"[?] {attr}: {value}")
        config_attr, config_value = next(gen)
        assert config_attr == attr
        assert config_value == value

    # Verify there are no remaining attributes
    with raises(StopIteration):
        next(gen)
