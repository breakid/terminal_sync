# -*- coding: utf-8 -*-
"""Defines a GhostWriter log entry"""

# Stardard Libraries
from dataclasses import asdict, dataclass
from datetime import datetime
from socket import AF_INET, gethostname, SOCK_DGRAM, socket
from typing import Optional


@dataclass
class Entry:
    """Defines a GhostWriter log entry

    Attributes:
        command (str): The text of the command executed
        start_time (str): Timestamp when the command/activity began
        end_time (str): Timestamp when the command/activity completed
        gw_id (Optional[int]): The log entry ID returned by GhostWriter
            Used to update the entry on completion
        source_host (Optional[str]): The host where the activity originated
        operator (Optional[str]): The name/identifier of the person creating the entry
        destination_host (Optional[str]): The target host of the activity
        tool (Optional[str]): The name/identifier of the tool used
        user_context (Optional[str]): Identifier for the credentials used for the command/activity
        output (str): The output or results of the command/activity
            Given the limited space in the GhostWriter UI, this is usually a success or failure note
        description (Optional[str]): The goal/intent/reason for running the command or performing the action
        comments (str): Misc additional information about the command / activity
        tags (Optional[list[str]]): An arbitrary list of tags
    """

    command: str
    start_time: str
    end_time: str
    gw_id: Optional[int] = None
    source_host: Optional[str] = None
    operator: Optional[str] = None
    destination_host: Optional[str] = None
    tool: Optional[str] = None
    user_context: Optional[str] = None
    output: str = ""
    description: Optional[str] = None
    comments: str = "Logged by terminal_sync"
    tags: Optional[list[str]] = None

    def __post_init__(self):
        # If source_host isn't specified, default to the host where the terminal_sync server is running
        self.source_host = self.source_host or self._get_local_host()

        self.command = self.command.strip()

        # Correct for differences in timestamps sent by the client versus set by the server
        if self.end_time < self.start_time:
            self.end_time = self.start_time

    def __iter__(self):
        """Iterate through an entry's attributes

        Yields:
            tuple[str, str]: A tuple containing an attribute name and its value
        """

        for attr, value in asdict(self).items():
            yield attr, value

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
        except:
            pass

        return f"{gethostname()} ({local_ip})"

    def fields(self) -> dict[str, Optional[int | str]]:
        """Return a dictionary of the entry's non-empty attributes

        Returns:
            dict[str, Optional[int | str]]: The entry's non-empty attributes
        """
        return {attr: value for attr, value in self if value is not None}

    def to_rest(self) -> dict[str, datetime | int | str]:
        """Return a dictionary of attributes using the keys expected by Ghostwriter's Oplog REST API

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

    def update(self, **kwargs) -> None:
        """Update specified attributes

        Args:
            **kwargs: Keyword arguments matching Entry attributes
        """
        for attr, value in kwargs.items():
            # Prevent accidentally overwriting values or adding attributes that shouldn't exist
            if value is not None and hasattr(self, attr) and attr != "start_time":
                setattr(self, attr, value)

        # Ensure the end_time is still equal to or greater than the start_time
        if self.end_time < self.start_time:
            self.end_time = self.start_time
