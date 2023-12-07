"""Test the _nolog plugin

Note: Automatically imports fixture from conftest.py
"""
# Third-party Libraries
from pytest import raises

# Internal Libraries
from terminal_sync import NoLogException
from terminal_sync.log_entry import Entry
from terminal_sync.plugins import _nolog as plugin


def test_basic_entry(basic_entry):
    assert plugin.process(basic_entry) == basic_entry, "Entry without "


def test_nolog_entry(nolog_entry):
    with raises(NoLogException) as e:
        plugin.process(nolog_entry)

        assert e.message == "terminal_sync.plugins._nolog"
