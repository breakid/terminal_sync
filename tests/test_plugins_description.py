"""Test the description plugin"""
# Standard Libraries
from os import environ

# Third-party Libraries
import pytest
from pytest import raises

# Internal Libraries
from terminal_sync.log_entry import Entry
from terminal_sync.plugins import _description as plugin


def test_process_no_token():
    entry: Entry = Entry(command="ps -ef")

    assert plugin.process(entry) is None


@pytest.mark.parametrize(
    "original_command, new_command, description_text",
    [
        # Token but no description text
        ("ps -ef #desc", "ps -ef", ""),
        # Token and description text
        ("ps -ef #desc This is a test", "ps -ef", "This is a test"),
    ],
)
def test_process_with_token(original_command, new_command, description_text):
    entry: Entry = Entry(command=original_command)

    entry = plugin.process(entry)

    assert entry is not None
    assert entry.command == new_command, f"Expected: {new_command}"
    assert entry.description == description_text, f"Expected: {description_text}"
