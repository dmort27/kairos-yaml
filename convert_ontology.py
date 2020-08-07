"""Converts events from KAIROS ontology spreadsheet into usable JSON format."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

JsonObject = Mapping[str, Any]


def read_events(sheet: pd.DataFrame) -> JsonObject:
    """Converts spreadsheet events into a usable format.

    Args:
        sheet: Contents of "events" sheet.

    Returns:
        Usable representation of events.
    """
    events = {}
    for row in sheet.iterrows():
        row = row[1]
        event_type = ".".join(
            t for t in [row["Type"], row["Subtype"], row["Sub-subtype"]] if t != "Unspecified"
        )
        event = {
            "id": row["AnnotIndexID"],
            "type": event_type,
            "definition": row["Definition"],
            "template": row["Template"],
            "args": {
                f"arg{i}": {
                    "position": f"arg{i}",
                    "label": row[f"arg{i} label"],
                    "constraints": row[f"arg{i} type constraints"],
                }
                for i in range(1, 7)
                if isinstance(row[f"arg{i} label"], str)
            },
        }
        events[event_type] = event
    return events


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in-file", type=Path, required=True,
                   help="Path to input KAIROS ontology Excel spreadsheet.")
    p.add_argument("--out-file", type=Path, required=True,
                   help="Path to output JSON.")
    args = p.parse_args()

    events_sheet = pd.read_excel(args.in_file, sheet_name="events")
    events = read_events(events_sheet)

    with open(args.out_file, "w") as file:
        json.dump(events, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
