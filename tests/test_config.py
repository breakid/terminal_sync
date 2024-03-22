"""Test the Config class"""

# Standard Libraries
from os import environ
from os import getenv
from os import unsetenv
from logging import DEBUG
from pathlib import Path
from typing import Any
from typing import Generator

# Third-party Libraries
import pytest
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
    "termsync_cache_dir": Path("json_logs"),
    "termsync_desc_token": "#desc",
    "termsync_enabled": False,
    "termsync_log_dir": Path("termsync_logs"),
    "termsync_nolog_token": "#dontlog",
    "termsync_save_all_local": True,
    # Aliased attributes
    "source_host": "192.168.1.2 (Ops VM)",
    "destination_host": "192.168.1.100 (LAB-DC01)",
    "oplog_id": 1,
}


def test_config_init():
    """Test that the Config object is populated properly from environment variables"""

    # Unset an environment variable to ensure the config will properly handle the value being missing
    environ["TERMSYNC_DESC_TOKEN"] = ""
    assert getenv("TERMSYNC_DESC_TOKEN") == ""

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


@pytest.mark.parametrize(
    "setting_name, test_value, expected_type",
    [
        ("gw_oplog_id", "five", "int"),
        ("gw_timeout_seconds", "ten", "int"),
    ],
)
def test_invalid_variable_type(setting_name: str, test_value: str, expected_type: str, caplog) -> None:
    # Save the original value so we can restore it later
    original_value = getenv(setting_name)

    environ[setting_name] = test_value

    with raises(SystemExit) as e:
        config: Config = Config()

    assert f"[-] {setting_name.upper()} is not a valid {expected_type}" in caplog.text

    assert e.type == SystemExit
    assert e.value.code == 1

    # Reset the environment variable to the original value so it doesn't interfere with subsequent tests
    environ[setting_name] = original_value


@pytest.mark.parametrize(
    "setting_name, valid_value, invalid_value, error_message",
    [
        ("termsync_desc_token", "#desc", "desc", "[-] termsync_desc_token must start with a '#'"),
        ("termsync_nolog_token", "#nolog", "nolog", "[-] termsync_nolog_token must start with a '#'"),
        (
            "gw_url",
            "https://ghostwriter.local",
            "not_a_url",
            "[-] Invalid Ghostwriter URL; activity will not be logged to Ghostwriter!",
        ),
        ("gw_oplog_id", "5", "-1", "[-] Oplog ID must be a positive integer"),
    ],
)
def test_setting_validation(
    setting_name: str, valid_value: str, invalid_value: str, error_message: str, caplog
) -> None:
    caplog.set_level(DEBUG)

    environ[setting_name] = valid_value
    config: Config = Config()

    assert error_message not in caplog.text
    assert "Ghostwriter logging enabled" in caplog.text

    environ[setting_name] = invalid_value
    config: Config = Config()
    assert error_message in caplog.text

    # Reset the environment variable to a valid value so it doesn't interfere with subsequent tests
    environ[setting_name] = valid_value


def test_invalid_api_tokens(caplog) -> None:
    caplog.set_level(DEBUG)

    environ["GW_API_KEY_GRAPHQL"] = ""
    environ["GW_API_KEY_REST"] = ""

    assert getenv("GW_API_KEY_GRAPHQL") == ""
    assert getenv("GW_API_KEY_REST") == ""

    config: Config = Config()

    assert "[-] No Ghostwriter API key specified; activity will not be logged to Ghostwriter!" in caplog.text
    assert "[*] Local logging enabled as a fallback" in caplog.text
