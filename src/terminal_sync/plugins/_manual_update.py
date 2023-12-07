# Internal Libraries
from terminal_sync.log_entry import Entry


# If gw_id attribute is set, the user is manually updating an entry, ensure it gets logged
def process(entry: Entry) -> Entry | None:
    return entry if entry.gw_id else None
