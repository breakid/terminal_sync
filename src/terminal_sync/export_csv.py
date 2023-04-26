"""Converts a terminal_sync JSON log archive to a GhostWriter-compatible CSV file.

It can be run as a standalone utility or called as a library, and was specifically designed with no external
dependencies so it can be run on any system, without terminal_sync needing to be installed.
"""
# Standard Libraries
from argparse import ArgumentParser
from csv import QUOTE_MINIMAL
from csv import DictWriter
from datetime import datetime
from json import load
from pathlib import Path


def export_csv(log_dir: Path, export_dir: Path = Path(".")) -> Path:
    """Generate a GhostWriter-compatible CSV file from all the JSON files in the specified log directory

    Args:
        log_dir (Path): The directory containing JSON logs
        export_dir (Path, optional): The directory where the CSV export will be written. Defaults to Path(".").

    Returns:
        str: The name of the exported CSV file
    """
    # Construct the CSV file output path with export timestamp
    csv_filepath: Path = Path(export_dir) / f"termsync_export_{datetime.utcnow().strftime('%F_%H%M%S')}.csv"
    json_filepath: Path

    csv_columns: list[str] = [
        "oplog_id",
        "start_date",
        "end_date",
        "source_ip",
        "dest_ip",
        "tool",
        "user_context",
        "command",
        "description",
        "output",
        "comments",
        "operator_name",
    ]

    # Open the CSV file and create a DictWriter
    with open(csv_filepath, "w", newline="") as csv_file:
        writer: DictWriter = DictWriter(csv_file, fieldnames=csv_columns, quoting=QUOTE_MINIMAL)

        writer.writeheader()

        # Iterate through each JSON file in the log_dir
        for json_filepath in log_dir.glob("*.json"):
            # Read the contents of the JSON file and add it as a row to the CSV file
            with open(json_filepath) as json_file:
                writer.writerow(load(json_file))

    return csv_filepath


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-l",
        "--log-dir",
        dest="log_dir",
        type=Path,
        required=True,
        help="The path to a directory containing terminal_sync JSON logs",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        default=".",
        type=Path,
        help="The directory where the CSV export will be written",
    )
    args = parser.parse_args()

    try:
        csv_filepath: Path = export_csv(args.log_dir, args.output_dir)
        print(f"[+] Successfully exported logs to: {csv_filepath}")
    except Exception as e:
        print(f"[-] Error: {e}")
