"""Defines a GhostWriter log entry class"""

# Standard Libraries
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Generator
from uuid import uuid4 as uuid


@dataclass
class Entry:
    """Defines a GhostWriter log entry

    Attributes:
        oplog_id (int): The ID of the GhostWriter Oplog where entries will be written
        command (str | None): The text of the command executed
        start_time (datetime): Timestamp when the command/activity began
        end_time (datetime): Timestamp when the command/activity completed
        gw_id (int | None): The log entry ID returned by GhostWriter
            Used to update the entry on completion
        source_host (str | None): The host where the activity originated
        operator (str | None): The name/identifier of the person creating the entry
        destination_host (str | None): The target host of the activity
        tool (str | None): The name/identifier of the tool used
        user_context (str | None): Identifier for the credentials used for the command/activity
        output (str | None): The output or results of the command/activity
            Given the limited space in the GhostWriter UI, this is usually a success or failure note
        description (str | None): The goal/intent/reason for running the command or performing the action
        comments (str | None): Misc additional information about the command / activity
    """

    # Note: Most of these default to None so that we don't accidentally overwrite attributes when updating an entry
    command: str | None = None
    comments: str = "Logged by terminal_sync"
    description: str | None = None
    destination_host: str | None = None
    start_time: datetime = datetime.utcnow()
    end_time: datetime = datetime.utcnow()
    gw_id: int | None = None
    operator: str | None = None
    oplog_id: int = 0
    output: str | None = None
    source_host: str | None = None
    tool: str | None = None
    user_context: str | None = None
    uuid: str = str(uuid())
    # TODO: Tags are not supported by the current GraphQL interface
    # tags (list[str] | None): An arbitrary list of tags
    # tags: list[str] = field(default_factory=list)

    def __iter__(self) -> Generator:
        """Iterate through an entry's attributes

        Yields:
            A tuple containing an attribute name and its value
        """
        yield from asdict(self).items()

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
        self._command = command.strip() if isinstance(command, str) else ""

    @property  # type: ignore[no-redef]
    def description(self) -> str:
        """Return the description

        Returns:
            str: The entry description
        """
        return self._description

    @description.setter
    def description(self, description: str) -> None:
        """Set the description, stripping whitespace from the beginning and end

        Args:
            description (str): The new description
        """
        self._description = description.strip() if isinstance(description, str) else ""

    @property  # type: ignore[no-redef]
    def start_time(self) -> str:
        """Return the start_time as a string in "YYYY-mm-dd HH:MM:SS" format

        Returns:
            str: The start_time in "YYYY-mm-dd HH:MM:SS" format
        """
        return self._start_time.strftime("%F %H:%M:%S")

    @start_time.setter
    def start_time(self, start_time: datetime | str) -> None:
        """Set the start_time

        Args:
            start_time (datetime | str): The new start_time
        """
        if start_time and isinstance(start_time, datetime):
            self._start_time = start_time
        elif start_time and isinstance(start_time, str):
            self._start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        else:
            self._start_time = datetime.utcnow()

    @property  # type: ignore[no-redef]
    def end_time(self) -> str:
        """Return the end_time as a string in "YYYY-mm-dd HH:MM:SS" format

        Returns:
            str: The end_time in "YYYY-mm-dd HH:MM:SS" format
        """
        return self._end_time.strftime("%F %H:%M:%S")

    @end_time.setter
    def end_time(self, end_time: datetime | str) -> None:
        """Set the end_time, making sure it's equal to or greater than the start_time

        Args:
            end_time (datetime | str): The new end_time
        """
        if end_time and isinstance(end_time, datetime):
            self._end_time = end_time
        elif end_time and isinstance(end_time, str):
            self._end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        else:
            self._end_time = datetime.utcnow()

        # Ensure end_date is a datetime object
        end_time = end_time if end_time and isinstance(end_time, datetime) else datetime.utcnow()

        # Note: Use _start_time rather than start_time to avoid:
        #   TypeError: '<' not supported between instances of 'datetime.datetime' and 'str'
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
        # Note: Used __dataclass_fields__ rather than hasattr() because hasattr() returns false unless the field
        # has a default value
        return cls(
            **{key: value for key, value in args.items() if key in cls.__dataclass_fields__ and value is not None}
        )

    def gw_fields(self) -> dict[str, int | str]:
        """Return a dictionary of non-empty entry attributes using the Ghostwriter field names

        Returns:
            A dictionary of fields for the GhostWriter REST API
        """
        # Map attribute names to REST API key names
        field_map: dict[str, str] = {
            "destination_host": "dest_ip",
            "end_time": "end_date",
            "operator": "operator_name",
            "source_host": "source_ip",
            "start_time": "start_date",
        }

        omitted_fields: list[str] = ["gw_id", "uuid"]

        # Construct a dictionary containing all non-empty entry attributes
        # Substitute the entry attribute name with the REST-specific field name
        return {
            field_map.get(attr, attr): value for attr, value in self if value is not None and attr not in omitted_fields
        }

    def json_filename(self) -> str:
        """Return a JSON filename for this entry with format: <oplog_id>_<start_time>_<uuid>.json

        This format ensures logs will first be grouped by oplog then listed chronologically

        Returns:
            str: The JSON filename for this entry
        """
        return f"{self.oplog_id}_{self._start_time.strftime('%F_%H%M%S')}_{self.uuid}.json"

    def fields(self) -> dict[str, int | str]:
        """Return a dictionary of the entry's non-empty attributes

        Returns:
            dict[str, int | str]: The entry's non-empty attributes
        """
        return {attr: value for attr, value in self if value is not None}

    def update(self, args: dict[str, Any]):
        """Update specified entry attributes

        Args:
            args (dict[str, Any]): A dictionary mapping attributes names to their new values
        """
        protected_fields: list[str] = ["oplog_id", "start_time", "uuid"]

        for attr, value in args.items():
            # Prevent accidentally overwriting values or adding attributes that shouldn't exist
            if value is not None and attr in self.__dataclass_fields__ and attr not in protected_fields:
                # if value is not None and self.hasattr(self, key) and key not in protected_fields:
                setattr(self, attr, value)

        return self
