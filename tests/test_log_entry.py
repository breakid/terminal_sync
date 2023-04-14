# Standard Libraries
from datetime import datetime

# Third-party Libraries
from pytest import fixture

# Internal Libraries
from terminal_sync.log_entry import Entry


@fixture
def basic_entry():
    return Entry(
        command="  proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL  ",
        start_time="2023-01-01 00:30:00",
        end_time="2023-01-01 00:29:00",  # One minute less than the start_time
    )


@fixture
def filled_out_entry():
    return Entry(
        command="  proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL  ",
        start_time="2022-12-01 09:30:00",
        end_time="2022-12-01 09:29:10",
        gw_id=1,
        source_host="localhost (127.0.0.1)",
        operator="neo",
        destination_host="",
        tool="smbclient.py",
        user_context="SGC.HWS.MIL/sam.carter",
        output="Success",
        description="Uploaded files to target",
        comments="PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130",
        tags=None,
    )


def test_entry_default_values(basic_entry):
    entry = basic_entry

    assert entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"

    assert entry.start_time == "2023-01-01 00:30:00"
    assert entry.end_time == "2023-01-01 00:30:00", f"Expected end_time to match start_time; got: {entry.end_time}"
    assert entry.gw_id is None
    assert entry.source_host is not None
    assert entry.operator is None
    assert entry.destination_host is None
    assert entry.tool is None
    assert entry.user_context is None
    assert entry.output == ""
    assert entry.description is None
    assert entry.comments == "Logged by terminal_sync"
    assert entry.tags is None


def test_entry_creation(filled_out_entry):
    entry = filled_out_entry

    assert entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    assert entry.start_time == "2022-12-01 09:30:00"
    assert entry.end_time == "2022-12-01 09:30:00"
    assert entry.gw_id == 1
    assert entry.source_host == "localhost (127.0.0.1)"
    assert entry.operator == "neo"
    assert entry.destination_host == ""
    assert entry.tool == "smbclient.py"
    assert entry.user_context == "SGC.HWS.MIL/sam.carter"
    assert entry.output == "Success"
    assert entry.description == "Uploaded files to target"
    assert entry.comments == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"
    assert entry.tags == None


def test_post_init_strips_command(basic_entry):
    assert (
        basic_entry.command == "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL"
    ), f'Spaces not stripped from: "{entry.command}"'


def test_post_init_resets_end_time(basic_entry):
    entry = basic_entry

    assert entry.start_time == "2023-01-01 00:30:00"
    assert entry.end_time == "2023-01-01 00:30:00", f"Expected end_time to match start_time; got: {entry.end_time}"


def test_entry_fields(filled_out_entry):
    fields = filled_out_entry.fields()

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
    assert "tags" not in fields


def test_to_rest(filled_out_entry):
    fields = filled_out_entry.to_rest()

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


def test_update(basic_entry):
    entry = basic_entry

    assert entry.start_time == "2023-01-01 00:30:00"
    assert entry.end_time == "2023-01-01 00:30:00"
    assert entry.output == ""
    assert entry.comments == "Logged by terminal_sync"

    entry.update(
        start_time="2023-01-02 00:30:00",
        end_time="2023-01-02 00:29:00",
        output="Success",
        comments="PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130",
    )

    assert entry.start_time == "2023-01-01 00:30:00", "Start time should not be updated"
    assert entry.end_time == "2023-01-02 00:29:00"
    assert entry.output == "Success"
    assert entry.comments == "PowerShell Session: bd58093b-9b74-4f49-b71f-7f6dcf4be130"

    entry.update(end_time="2023-01-01 00:00:00")

    assert entry.end_time == "2023-01-01 00:30:00", "End time set to before start time should be reset to start time"


# def test_iter(basic_entry):
#     attrs: dict[str, Optional[str]] = {
#         "command": "proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL",
#         "start_time": "2022-12-28 23:55:59",
#         "end_time": "2022-12-28 23:55:59",
#         "uuid": None,
#         "gw_id": None,
#         "source_host": None,
#         "operator": None,
#         "destination_host": None,
#         "tool": None,
#         "user_context": None,
#         "output": "",
#         "description": None,
#         "comments": "Logged by terminal_sync",
#         "tags": None,
#     }

#     for attr, value in attrs.items():
#         assert basic_entry.__iter__() == (attr, value)
