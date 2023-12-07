"""Test the proxychains plugin
"""
# Third-party Libraries
import pytest

# Internal Libraries
from terminal_sync.log_entry import Entry
from terminal_sync.plugins import proxychains


@pytest.mark.parametrize(
    "test_input, expected",
    [
        # No trigger phrase
        ("Ps -ef", None),
        # Not a command
        ("vim /etc/proxychains.conf", None),
        # Trigger but no tool name
        ("proxychains4 -q", None),
        # Trigger but no tool name
        ("proxychains4 -f ~/proxychains.conf", None),
        # Parses tool name
        ("proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL", "python3"),
        # Parses tool name when proxychains is run with arguments
        (
            "proxychains4 -q -f /root/proxychains.conf python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
            "python3",
        ),
        # Parses tool name when proxychains is not at the beginning of the command
        (
            "ps -ef; proxychains4 -q python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
            "python3",
        ),
        # Invalid proxychains argument
        (
            "ps -ef; proxychains4 -a python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
            None,
        ),
    ],
)
def test_get_tool_name(test_input, expected):
    if expected is None:
        assert proxychains.get_tool_from_proxychains(test_input) is None, "Expected: None"
    else:
        assert proxychains.get_tool_from_proxychains(test_input) == expected, f"Expected: {expected}"


@pytest.mark.parametrize(
    "test_input, expected",
    [
        # Not a command
        ("vim /etc/proxychains.conf", False),
        # Trigger but no tool name
        ("proxychains4 -q", True),
        # Parses tool name
        ("proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL", True),
        # Parses tool name when proxychains is run with arguments
        (
            "proxychains4 -q -f /root/proxychains.conf python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
            True,
        ),
    ],
)
def test_match(test_input, expected):
    assert proxychains.match(test_input) == expected, f"Expected: {expected}"


@pytest.mark.parametrize(
    "test_input, expected",
    [
        # Not a command
        ("vim /etc/proxychains.conf", None),
        # Trigger but no tool name
        ("proxychains4 -q", None),
        # Parses tool name
        ("proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL", "python3"),
        # Parses tool name when proxychains is run with arguments
        (
            "proxychains4 -q -f /root/proxychains.conf python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
            "python3",
        ),
    ],
)
def test_process(test_input, expected):
    entry: Entry = Entry(command=test_input)

    if expected is None:
        assert proxychains.process(entry) is None, "Expected: None"
    else:
        assert proxychains.process(entry).tool == expected, f"Expected: {expected}"
