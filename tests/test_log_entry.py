# Standard Libraries
from datetime import datetime
from re import Pattern
from re import compile
from typing import Any
from typing import Generator

# Third-party Libraries
from pytest import fixture
from pytest import raises

# Internal Libraries
from terminal_sync.log_entry import Entry

# Define common patterns that can be reused in multiple tests
DATE_PATTERN: Pattern = compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
HOST_PATTERN: Pattern = compile(r".*? \(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\)")


@fixture
def basic_entry() -> Entry:
    """Return a new Entry object using only mandatory arguments

    Returns:
        Entry: An Entry object with only mandatory fields set
    """
    return Entry(command="  proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL  ")


@fixture
def filled_out_entry() -> Entry:
    """Return a new Entry object using all arguments

    Returns:
        Entry: An Entry object with all fields set
    """
    return Entry(
        command="  proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL  ",
        comments="PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130",
        description="Uploaded files to target",
        destination_host="",
        end_time=datetime.fromisoformat("2022-12-01 09:29:10"),  # 50 seconds less than the start time
        gw_id=2,
        oplog_id=1,
        operator="neo",
        output="Success",
        source_host="localhost (127.0.0.1)",
        start_time=datetime.fromisoformat("2022-12-01 09:30:00"),
        tool="smbclient.py",
        user_context="SGC.HWS.MIL/sam.carter",
        uuid="c8f897a6-d3c9-4432-8d29-4df99773892d.18",
        # tags=None,
    )


def test_creation(filled_out_entry: Entry) -> None:
    """Verify all fields are set properly when creating an entry

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    entry: Entry = filled_out_entry

    assert (
        entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    ), f"Expected whitespace to be stripped from the command; got '{entry.command}'"
    assert entry.comments == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    assert entry.description == "Uploaded files to target"
    assert entry.destination_host == ""
    assert entry.end_time == "2022-12-01 09:30:00", f"Expected end_time to match start_time; got: {entry.end_time}"
    assert entry.gw_id == 2
    assert entry.operator == "neo"
    assert entry.oplog_id == 1
    assert entry.output == "Success"
    assert entry.start_time == "2022-12-01 09:30:00"
    assert entry.source_host == "localhost (127.0.0.1)"
    assert entry.tool == "smbclient.py"
    assert entry.user_context == "SGC.HWS.MIL/sam.carter"
    assert entry.uuid == "c8f897a6-d3c9-4432-8d29-4df99773892d.18"
    # assert entry.tags is None


def test_default_values(basic_entry: Entry) -> None:
    """Verify default values are set

    Args:
        basic_entry (Entry): An Entry object with only mandatory fields set
    """
    entry: Entry = basic_entry

    assert (
        entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    ), f"Expected whitespace to be stripped from the command; got '{entry.command}'"
    assert entry.comments == "Logged by terminal_sync"
    assert entry.description == ""
    assert entry.destination_host is None
    assert isinstance(entry.end_time, str) and DATE_PATTERN.match(entry.end_time)
    assert entry.gw_id is None
    assert entry.operator is None
    assert entry.oplog_id == 0
    assert entry.output == ""
    assert isinstance(entry.source_host, str) and HOST_PATTERN.match(
        entry.source_host
    ), f"Expected source_host to be a string with pattern '<hostname> (<IP>)'; got {type(entry.source_host)}"
    assert isinstance(entry.start_time, str) and DATE_PATTERN.match(entry.start_time)
    assert entry.tool is None
    assert entry.user_context is None
    assert entry.uuid == ""
    # assert entry.tags is None


def test_fields(filled_out_entry: Entry) -> None:
    """Verify `.fields()` returns the correct values

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    fields: dict[str, int | str] = filled_out_entry.fields()

    assert len(fields) == 14, f"Expected 14; got {fields}"
    assert fields["command"] == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    assert fields["comments"] == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    assert fields["description"] == "Uploaded files to target"
    assert fields["destination_host"] == ""
    assert fields["end_time"] == "2022-12-01 09:30:00"
    assert fields["gw_id"] == 2
    assert fields["operator"] == "neo"
    assert fields["oplog_id"] == 1
    assert fields["output"] == "Success"
    assert fields["source_host"] == "localhost (127.0.0.1)"
    assert fields["start_time"] == "2022-12-01 09:30:00"
    assert fields["tool"] == "smbclient.py"
    assert fields["user_context"] == "SGC.HWS.MIL/sam.carter"
    assert fields["uuid"] == "c8f897a6-d3c9-4432-8d29-4df99773892d.18"
    # assert "tags" not in fields


def test_gw_fields(filled_out_entry: Entry) -> None:
    """Verify `.gw_fields()` returns the correct keys and values

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    fields: dict[str, int | str] = filled_out_entry.gw_fields()

    assert len(fields) == 12, f"Expected 12; got {fields}"
    assert fields["command"] == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    assert fields["comments"] == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    assert fields["description"] == "Uploaded files to target"
    assert fields["dest_ip"] == ""
    assert fields["end_date"] == "2022-12-01 09:30:00"
    assert fields["operator_name"] == "neo"
    assert fields["oplog_id"] == 1
    assert fields["output"] == "Success"
    assert fields["source_ip"] == "localhost (127.0.0.1)"
    assert fields["start_date"] == "2022-12-01 09:30:00"
    assert fields["tool"] == "smbclient.py"
    assert fields["user_context"] == "SGC.HWS.MIL/sam.carter"


def test_iter(filled_out_entry) -> None:
    """Verify the `__iter__()` function successfully loops through all attributes and returns the correct values

    Args:
        filled_out_entry (_type_): An Entry object with all fields set
    """
    attrs: dict[str, int | str] = {
        "command": "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
        "comments": "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130",
        "description": "Uploaded files to target",
        "destination_host": "",
        "start_time": "2022-12-01 09:30:00",
        "end_time": "2022-12-01 09:30:00",
        "gw_id": 2,
        "operator": "neo",
        "oplog_id": 1,
        "output": "Success",
        "source_host": "localhost (127.0.0.1)",
        "tool": "smbclient.py",
        "user_context": "SGC.HWS.MIL/sam.carter",
        "uuid": "c8f897a6-d3c9-4432-8d29-4df99773892d.18",
        # "tags": None,
    }
    entry_attr: str
    entry_value: Any

    gen: Generator = filled_out_entry.__iter__()

    assert isinstance(gen, Generator)

    # Verify the correct values are returned
    for attr, value in attrs.items():
        entry_attr, entry_value = next(gen)
        assert entry_attr == attr
        assert entry_value == value

    # Verify there are no remaining attributes
    with raises(StopIteration):
        next(gen)


def test_json_filename(filled_out_entry) -> None:
    """Verify the JSON filename is constructed properly

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    entry: Entry = filled_out_entry

    assert entry.json_filename() == "1_2022-12-01_093000_c8f897a6-d3c9-4432-8d29-4df99773892d.18.json"


def test_update(filled_out_entry: Entry) -> None:
    """Verify that `update()` updates the end_time, output, and comments; does not update start_time;
    and ignores keys that do not match attributes

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    entry: Entry = filled_out_entry

    original_start_time: str = "2022-12-01 09:30:00"
    new_end_time: str = "2023-01-02 00:29:00"
    new_output: str = "Failed"
    new_comment: str = "PowerShell Session: 7f007022-1cb6-4e8d-b8b8-252e6e07943d"

    # Baseline the previous state
    assert entry.comments == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    assert entry.end_time == "2022-12-01 09:30:00"
    assert entry.output == "Success"
    assert entry.start_time == original_start_time

    # 'invalid_key' should be ignored gracefully and not raise an exception
    entry.update(
        {
            "comments": new_comment,
            "end_time": datetime.fromisoformat(new_end_time),
            "invalid_key": "",
            "output": new_output,
            "start_time": datetime.fromisoformat("2023-01-02 00:30:00"),
        }
    )

    # Verify start_time was not updated and the remaining fields were
    assert entry.comments == new_comment
    assert entry.end_time == new_end_time, f"End time should be updated; got: {entry.end_time}"
    assert entry.output == new_output, f"Expected '{new_output}'; got: {entry.output}"
    assert entry.start_time == original_start_time, f"Start time should not be updated; got: {entry.start_time}"

    # Verify if end_time < start_time, the end_time is set to match start_time
    new_end_time = "2022-11-30 00:00:00"
    entry.update({"end_time": datetime.fromisoformat(new_end_time)})

    assert new_end_time < original_start_time
    assert entry.end_time == original_start_time, "End time set to before start time should be reset to start time"
