"""Test the manual_update plugin

Note: Automatically imports fixture from conftest.py
"""

# Third-party Libraries
import pytest

# Internal Libraries
from terminal_sync.log_entry import Entry
from terminal_sync.plugins import _manual_update as plugin


def test_entry_without_gw_id(basic_entry):
    assert basic_entry.gw_id is None
    assert plugin.process(basic_entry) is None


def test_entry_with_gw_id(filled_out_entry):
    assert filled_out_entry.gw_id is not None
    assert plugin.process(filled_out_entry) == filled_out_entry
