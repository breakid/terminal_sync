"""Defines a GhostWriter log entry class"""

# Standard Libraries
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from socket import AF_INET
from socket import SOCK_DGRAM
from socket import gethostname
from socket import socket
from typing import Any
from typing import Generator


@dataclass
class Entry:
    """Defines a GhostWriter log entry

    Attributes:
        command (str): The text of the command executed
        start_time (datetime): Timestamp when the command/activity began
        end_time (datetime): Timestamp when the command/activity completed
        gw_id (int | None): The log entry ID returned by GhostWriter
            Used to update the entry on completion
        source_host (str | None): The host where the activity originated
        operator (str | None): The name/identifier of the person creating the entry
        destination_host (str | None): The target host of the activity
        tool (str | None): The name/identifier of the tool used
        user_context (str | None): Identifier for the credentials used for the command/activity
        output (str): The output or results of the command/activity
            Given the limited space in the GhostWriter UI, this is usually a success or failure note
        description (str | None): The goal/intent/reason for running the command or performing the action
        comments (str): Misc additional information about the command / activity
    """

    command: str
    start_time: datetime = datetime.utcnow()
    end_time: datetime = datetime.utcnow()
    gw_id: int | None = None
    source_host: str | None = None
    operator: str | None = None
    destination_host: str | None = None
    tool: str | None = None
    user_context: str | None = None
    output: str = ""
    description: str | None = None
    comments: str = "Logged by terminal_sync"
    # TODO: Tags are not supported by the current GraphQL interface
    # tags (list[str] | None): An arbitrary list of tags
    # tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize source_host to the local host if not explicitly set"""
        self.source_host = self.source_host or self._get_local_host()

    def __iter__(self) -> Generator:
        """Iterate through an entry's attributes

        Yields:
            A tuple containing an attribute name and its value
        """
        yield from asdict(self).items()

    def _get_local_host(self) -> str:
        """Return the hostname and IP address of the local host

        Returns:
            str: The hostname and IP address of the local host (e.g., "WORKSTATION (192.168.1.20)")
        """
        local_ip: str = "127.0.0.1"

        try:
            # connect() for UDP doesn't send packets but can be used to determine the primary NIC
            s: socket = socket(AF_INET, SOCK_DGRAM)
            s.connect(("8.8.8.8", 0))
            local_ip = s.getsockname()[0]
        except Exception:
            pass

        return f"{gethostname()} ({local_ip})"

    @property  # type: ignore[no-redef]
    def command(self) -> str:
        """Return the command

        Returns:
            str: The command
        """
        return self._command

    @command.setter
    def command(self, command: str) -> None:
        """Set the command, stripping whitespace from the beginning and end

        Args:
            command (str): The new command value
        """
        # Note: Omitting this isinstance() check caused the code to generate:
        # "AttributeError: 'property' object has no attribute 'strip'"
        # if the command was not explicitly set when initializing an object
        # (even when a default value was provided)
        self._command = "" if isinstance(command, property) else command.strip()

    @property  # type: ignore[no-redef]
    def start_time(self) -> str:
        """Return the start_time as a string in "YYYY-mm-dd HH:MM:SS" format

        Returns:
            str: The start_time in "YYYY-mm-dd HH:MM:SS" format
        """
        return self._start_time.strftime("%F %H:%M:%S")

    @start_time.setter
    def start_time(self, start_time: datetime) -> None:
        """Set the start_time

        Args:
            start_time (datetime): The new start_time
        """
        self._start_time = datetime.utcnow() if isinstance(start_time, property) else start_time

    @property  # type: ignore[no-redef]
    def end_time(self) -> str:
        """Return the end_time as a string in "YYYY-mm-dd HH:MM:SS" format

        Returns:
            str: The end_time in "YYYY-mm-dd HH:MM:SS" format
        """
        return self._end_time.strftime("%F %H:%M:%S")

    @end_time.setter
    def end_time(self, end_time: datetime) -> None:
        """Set the end_time, making sure it's equal to or greater than the start_time

        Args:
            end_time (datetime): The new end_time
        """
        end_time = datetime.utcnow() if isinstance(end_time, property) else end_time

        if end_time < self._start_time:
            self._end_time = self._start_time
        else:
            self._end_time = end_time

    @classmethod
    def from_dict(cls, args: dict[str, Any]):
        """Return a new Entry object populated from the provided dictionary

        This method filters out all key-value pairs that are not Entry attributes and uses the valid ones
        to create a new Entry object

        Args:
            args (dict[str, Any]): A dictionary containing Entry attributes and associated values

        Returns:
            Entry: The new Entry object
        """
        return cls(**{key: value for key, value in args.items() if hasattr(cls, key)})

    def fields(self) -> dict[str, int | str]:
        """Return a dictionary of the entry's non-empty attributes

        Returns:
            dict[str, int | str]: The entry's non-empty attributes
        """
        return {attr: value for attr, value in self if value is not None}

    def to_rest(self) -> dict[str, int | str]:
        """Return a dictionary of non-empty entry attributes using the keys expected by Ghostwriter's Oplog REST API

        Returns:
            A dictionary of fields for the GhostWriter REST API
        """
        # Map attribute names to REST API key names
        field_map: dict[str, str] = {
            "end_time": "end_date",
            "operator": "operator_name",
            "source_host": "source_ip",
            "start_time": "start_date",
        }

        # Construct a dictionary containing all non-empty entry attributes
        # Substitute the entry attribute name with the REST-specific field name
        return {field_map.get(attr, attr): value for attr, value in self if value is not None}

    def update(self, args: dict[str, Any]) -> None:
        """Update specified entry attributes

        Args:
            args (dict[str, Any]): A dictionary mapping attributes names to their new values
        """
        for attr, value in args.items():
            # Prevent accidentally overwriting values or adding attributes that shouldn't exist
            if value is not None and hasattr(self, attr) and attr != "start_time":
                setattr(self, attr, value)

        # Ensure the end_time is still equal to or greater than the start_time
        # if self.end_time < self.start_time:
        #     self.end_time = self.start_time
