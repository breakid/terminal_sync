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
        start_time=datetime.fromisoformat("2022-12-01 09:30:00"),
        end_time=datetime.fromisoformat("2022-12-01 09:29:10"),  # 50 seconds less than the start time
        gw_id=1,
        source_host="localhost (127.0.0.1)",
        operator="neo",
        destination_host="",
        tool="smbclient.py",
        user_context="SGC.HWS.MIL/sam.carter",
        output="Success",
        description="Uploaded files to target",
        comments="PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130",
        # tags=None,
    )


def test_entry_default_values(basic_entry: Entry) -> None:
    """Verify default values are set

    Args:
        basic_entry (Entry): An Entry object with only mandatory fields set
    """
    entry: Entry = basic_entry

    assert (
        entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    ), f"Expected whitespace to be stripped from the command; got '{entry.command}'"
    assert isinstance(entry.start_time, str)
    assert isinstance(entry.end_time, str)
    assert DATE_PATTERN.match(entry.start_time)
    assert DATE_PATTERN.match(entry.end_time)
    assert entry.gw_id is None
    assert isinstance(entry.source_host, str), f"Expected source_host to be a string; got {type(entry.source_host)}"
    assert HOST_PATTERN.match(entry.source_host)
    assert entry.operator is None
    assert entry.destination_host is None
    assert entry.tool is None
    assert entry.user_context is None
    assert entry.output == ""
    assert entry.description is None
    assert entry.comments == "Logged by terminal_sync"
    # assert entry.tags is None


def test_entry_creation(filled_out_entry: Entry) -> None:
    """Verify all fields are set properly when creating an entry

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    entry: Entry = filled_out_entry

    assert (
        entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    ), f"Expected whitespace to be stripped from the command; got '{entry.command}'"
    assert entry.start_time == "2022-12-01 09:30:00"
    assert entry.end_time == "2022-12-01 09:30:00", f"Expected end_time to match start_time; got: {entry.end_time}"
    assert entry.gw_id == 1
    assert entry.source_host == "localhost (127.0.0.1)"
    assert entry.operator == "neo"
    assert entry.destination_host == ""
    assert entry.tool == "smbclient.py"
    assert entry.user_context == "SGC.HWS.MIL/sam.carter"
    assert entry.output == "Success"
    assert entry.description == "Uploaded files to target"
    assert entry.comments == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    # assert entry.tags is None


def test_entry_fields(filled_out_entry: Entry) -> None:
    """Verify `.fields()` returns the correct values

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    fields: dict[str, int | str] = filled_out_entry.fields()

    assert len(fields) == 12
    assert fields["command"] == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    assert fields["start_time"] == "2022-12-01 09:30:00"
    assert fields["end_time"] == "2022-12-01 09:30:00"
    assert fields["gw_id"] == 1
    assert fields["source_host"] == "localhost (127.0.0.1)"
    assert fields["operator"] == "neo"
    assert fields["destination_host"] == ""
    assert fields["tool"] == "smbclient.py"
    assert fields["user_context"] == "SGC.HWS.MIL/sam.carter"
    assert fields["output"] == "Success"
    assert fields["description"] == "Uploaded files to target"
    assert fields["comments"] == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    # assert "tags" not in fields


def test_to_rest(filled_out_entry: Entry) -> None:
    """_summary_

    Args:
        filled_out_entry (Entry): An Entry object with all fields set
    """
    fields: dict[str, int | str] = filled_out_entry.to_rest()

    assert len(fields) == 12
    assert fields["command"] == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    assert fields["start_date"] == "2022-12-01 09:30:00"
    assert fields["end_date"] == "2022-12-01 09:30:00"
    assert fields["gw_id"] == 1
    assert fields["source_ip"] == "localhost (127.0.0.1)"
    assert fields["operator_name"] == "neo"
    assert fields["destination_host"] == ""
    assert fields["tool"] == "smbclient.py"
    assert fields["user_context"] == "SGC.HWS.MIL/sam.carter"
    assert fields["output"] == "Success"
    assert fields["description"] == "Uploaded files to target"
    assert fields["comments"] == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"


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
    assert entry.start_time == original_start_time
    assert entry.end_time == "2022-12-01 09:30:00"
    assert entry.output == "Success"
    assert entry.comments == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"

    # 'invalid_key' should be ignored gracefully and not raise an exception
    entry.update(
        {
            "start_time": datetime.fromisoformat("2023-01-02 00:30:00"),
            "end_time": datetime.fromisoformat(new_end_time),
            "output": new_output,
            "comments": new_comment,
            "invalid_key": "",
        }
    )

    # Verify start_time was not updated and the remaining fields were
    assert entry.start_time == original_start_time, f"Start time should not be updated; got: {entry.start_time}"
    assert entry.end_time == new_end_time, f"End time should be updated; got: {entry.end_time}"
    assert entry.output == new_output, f"Expected '{new_output}'; got: {entry.output}"
    assert entry.comments == new_comment

    # Verify if end_time < start_time, the end_time is set to match start_time
    new_end_time = "2022-11-30 00:00:00"
    entry.update({"end_time": datetime.fromisoformat(new_end_time)})

    assert new_end_time < original_start_time
    assert entry.end_time == original_start_time, "End time set to before start time should be reset to start time"


def test_iter(filled_out_entry) -> None:
    """Verify the `__iter__()` function successfully loops through all attributes and returns the correct values

    Args:
        filled_out_entry (_type_): An Entry object with all fields set
    """
    attrs: dict[str, int | str] = {
        "command": "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
        "start_time": "2022-12-01 09:30:00",
        "end_time": "2022-12-01 09:30:00",
        "gw_id": 1,
        "source_host": "localhost (127.0.0.1)",
        "operator": "neo",
        "destination_host": "",
        "tool": "smbclient.py",
        "user_context": "SGC.HWS.MIL/sam.carter",
        "output": "Success",
        "description": "Uploaded files to target",
        "comments": "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130",
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


# if __name__ == "__main__":
#     test_update(filled_out_entry())
