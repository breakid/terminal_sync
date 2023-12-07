# Standard Libraries
from datetime import datetime
from uuid import UUID

# Third-party Libraries
from pytest import fixture

# Internal Libraries
from terminal_sync import cfg as config
from terminal_sync.ghostwriter import GhostwriterClient
from terminal_sync.log_entry import Entry


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

@fixture
def nolog_entry() -> Entry:
    """Return a new Entry object with the nolog token in the command

    Returns:
        Entry: An Entry object with the nolog token in the command
    """
    return Entry(command=f"  proxychains4 python3 smbclient.py SGC.HWS.MIL/sam.carter:password@SGCDC001.SGC.HWS.MIL   {config.termsync_nolog_token}")


# =============================================================================
#                               Helper Functions
# =============================================================================

# Technique for helper functions from: https://stackoverflow.com/a/42156088


class Helpers:
    @staticmethod
    def is_uuid(test_value: str) -> bool:
        try:
            UUID(test_value)
        except ValueError:
            return False

        return True


@fixture
def helpers():
    return Helpers
