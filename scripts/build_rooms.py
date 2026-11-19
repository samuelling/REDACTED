"""Group Data Set 1 search photos into rooms by the FBI room placards.

Reads the kabasshouse/epstein-data `documents` shard that holds Data Set 1,
finds the placard photos ("B Search Personnel ... Search Completed"), and
assigns every following photo to that placard until the next one appears.

Output: data/rooms.json (git-ignored) -- a list of segments in shooting order:
    {"seq", "label", "efta_start", "efta_end", "photos": [{"efta", "text"}]}

Usage:
    python scripts/build_rooms.py path/to/documents-00000.parquet
"""

import json
import re
import sys
from pathlib import Path

import duckdb

PLACARD = re.compile(
    r"Search (Personnel|Warrant|Completed|Process)|Batch Process|Description of Room"
)
LABEL = r"([A-Z]{1,2}|0)"  # room codes run A..Z then AA..NN; OCR reads O as 0


def efta_num(key: str) -> int:
    return int(re.sub(r"\D", "", key))


def clean(text: str) -> str:
    """Drop the Bates stamp, which appears on every page."""
    text = re.sub(r"EFT\s?A\s?[O0-9]{8,9}", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def placard_label(text: str) -> str | None:
    """Pull the room code from a placard's OCR text, wherever it landed."""
    t = clean(text)
    patterns = [
        rf"^(?:LOCATION\s+)?{LABEL}\s",              # "B Search ..."
        rf"Description of Rooms?\s+{LABEL}\s",        # "Description of Room C Search ..."
        rf"Building Name\s+{LABEL}\s",
        rf"\(Place X in Box\)\s+{LABEL}$",           # code read after the form text
        rf"Completed Date & Time\s+{LABEL}$",
    ]
    for p in patterns:
        m = re.search(p, t, re.I if "Description" in p else 0)
        if m:
            code = m.group(1).upper()
            return "O" if code == "0" else code
    return None


def main(parquet: str) -> None:
    rows = duckdb.sql(
        f"""
        SELECT file_key, full_text, is_photo
        FROM read_parquet('{parquet}')
        WHERE dataset = 'DataSet1'
        ORDER BY file_key
        """
    ).fetchall()

    segments, current = [], None
    for key, text, _ in rows:
        n = efta_num(key)
        if PLACARD.search(text or ""):
            current = {
                "seq": len(segments),
                "label": placard_label(text) or "?",
                "efta_start": n,
                "efta_end": n,
                "photos": [],
            }
            segments.append(current)
            continue
        if current is None:  # photos before the first placard
            current = {"seq": 0, "label": "pre", "efta_start": n, "efta_end": n, "photos": []}
            segments.append(current)
        current["photos"].append({"efta": n, "text": clean(text)})
        current["efta_end"] = n

    out = Path(__file__).resolve().parent.parent / "data" / "rooms.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(segments, indent=1))

    texted = sum(1 for s in segments for p in s["photos"] if len(p["text"]) >= 20)
    total = sum(len(s["photos"]) for s in segments)
    print(f"{len(segments)} segments, {total} photos, {texted} with legible text -> {out}")
    for s in segments:
        print(f'{s["seq"]:3d} {s["label"]:>4} EFTA {s["efta_start"]:>5}-{s["efta_end"]:<5} {len(s["photos"]):4d} photos')


if __name__ == "__main__":
    main(sys.argv[1])
