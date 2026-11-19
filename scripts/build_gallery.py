"""Sort the inventory by type and place, for a gallery arranged by what things are.

    python scripts/build_gallery.py DOCUMENTS_PARQUET   # -> site/gallery.json

Reads site/inventory.json (objects and frames with their EFTA numbers), the
Data Set 1 scene descriptions, and the FBI evidence-recovery log from
kabasshouse/epstein-data. Writes:
  objects:  {category: [[EFTA, matched word, position in shooting order], ...]}
  frames:   {place: [[EFTA, status, description, position], ...]}
  evidence: [[item number, short description, place, file_key, dataset], ...]
Evidence descriptions are reduced to plain item types; anything sexual or
showing people is reduced to a neutral label and never described.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent

# Where each kind of photograph hangs, from its scene description (first match wins).
PLACES = [
    ("massage", r"massage"),
    ("bath", r"bathroom|toilet|\bsink\b|vanity|shower|bathtub|\btub\b"),
    ("kitchen", r"kitchen|pantry|refrigerator|stove|oven|wine"),
    ("laundry", r"laundry|washer|dryer|washing machine|linen"),
    ("closet", r"closet|wardrobe|walk-in|hanging clothes|shoe"),
    ("bedroom", r"bedroom|\bbed\b|nightstand"),
    ("gym", r"\bgym\b|exercise|treadmill|weights|workout|boxing"),
    ("library", r"library|bookshel|bookcase|books"),
    ("situation", r"server|network|\brack\b|router|cctv|monitors|security camera|surveillance"),
    ("office", r"\boffice\b|\bdesk\b|\bstudy\b|computer|printer"),
    ("mechanical", r"mechanical|boiler|utility room|electrical panel|\bpipes?\b|valve|water heater|breaker|\bhvac\b|duct"),
    ("vault", r"\bsafe\b|vault"),
    ("sitting", r"living room|sitting room|\bsofa\b|\bcouch\b|piano|fireplace|dining"),
    ("hall", r"hallway|corridor|stair|foyer|entrance|doorway|landing|elevator"),
    ("ballroom", r"."),
]
PLACES = [(k, re.compile(v, re.I)) for k, v in PLACES]

SEXUAL = re.compile(r"sex|penis|vagina|dildo|vibrator|adult|erotic|nude|naked|porn|lubric|condom|torpedo", re.I)
PEOPLE = re.compile(r"photo|picture|people|person|girl|woman|women|man\b|men\b|child|portrait|image", re.I)
LOC = [
    ("bedroom", r"bed ?room|living quarters|master"), ("kitchen", r"kitchen"), ("bath", r"bath"),
    ("closet", r"closet"), ("office", r"desk|office|study"), ("library", r"book ?case|shel"),
    ("massage", r"massage"), ("ballroom", r"suburban|vehicle|car\b|garage|chevrolet"),
]
LOC = [(k, re.compile(v, re.I)) for k, v in LOC]


def place_of(desc: str) -> str:
    for k, rx in PLACES:
        if rx.search(desc or ""):
            return k
    return "ballroom"


TYPES = [  # plain item types; anything else is not described
    (r"message (book|pad)|phone message", "Phone message book"), (r"massage table|message table", "Massage table"),
    (r"\bcpu\b|computer tower", "Computer tower (CPU)"), (r"power cord", "Power cord"), (r"vhs|8 ?mm|video tape", "Video tapes"),
    (r"\bzip\b", "Zip disks"), (r"floppy|disks? in|drive disk|\bdisks\b", "Disks"), (r"compact flash|flash card", "Camera flash cards"),
    (r"cd|compact dis", "CDs"), (r"shredded", "Shredded paper"), (r"soap", "Soap"), (r"cotton swab", "Cotton swabs"),
    (r"rental agreement", "Rental agreement"), (r"receipt", "Receipts"), (r"bible", "Bible"), (r"\bbooks?\b", "Books"),
    (r"phone", "Telephone"), (r"rope", "Rope"), (r"file|folder|records|paper", "Files (not described)"),
]
TYPES = [(re.compile(a, re.I), b) for a, b in TYPES]


def evidence_label(desc: str) -> str:
    d = (desc or "").strip()
    if SEXUAL.search(d) or re.search(r"jelly|oil|lotion", d, re.I):
        return "Adult items (not depicted)"
    if PEOPLE.search(d) or re.search(r"school|transcript|note from|letter|id\b|passport|license", d, re.I):
        return "Photographs or personal papers (not reproduced)" if PEOPLE.search(d) else "Personal papers (not described)"
    for rx, label in TYPES:
        if rx.search(d):
            return label
    return "Item (not described)"


def main(docs: str) -> None:
    inv = json.loads((ROOT / "site" / "inventory.json").read_text())
    order = {}
    for r in inv["rooms"]:
        for e in range(r["efta_start"], r["efta_end"] + 1):
            order[e] = len(order) + 1
    notes = dict(duckdb.sql(f"SELECT CAST(regexp_replace(file_key,'\\D','','g') AS INT), coalesce(additional_notes,'') "
                            f"FROM read_parquet('{docs}') WHERE dataset='DataSet1'").fetchall())

    objects = defaultdict(list)
    frames = defaultdict(list)
    for r in inv["rooms"]:
        for cat, efta, term in r["items"]:
            objects[cat].append([efta, term, order.get(efta, 0)])
        for efta, status, desc in r["frames"]:
            frames[place_of(notes.get(efta, ""))].append([efta, status, desc, order.get(efta, 0)])

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    ev = con.execute("SELECT item_number, item_description, location_found, file_key, dataset "
                     "FROM 'hf://datasets/kabasshouse/epstein-data/data/investigative_records/*.parquet' "
                     "WHERE record_type = 'evidence_recovery_log'").fetchall()
    evidence = []
    for num, desc, loc, key, ds in ev:
        where = next((k for k, rx in LOC if rx.search(loc or "")), None) or ("massage" if re.search(r"massage", desc or "", re.I) else "office")
        evidence.append([num or "", evidence_label(desc), where, key, ds])

    out = {"redaction_fragments": inv["redaction_fragments"], "photos": len(order), "objects": objects, "frames": frames, "evidence": evidence}
    (ROOT / "site" / "gallery.json").write_text(json.dumps(out, separators=(",", ":")))
    print({k: len(v) for k, v in frames.items()})
    print({k: len(v) for k, v in objects.items()})
    print(len(evidence), "evidence items;", {k: sum(1 for e in evidence if e[2] == k) for k in set(e[2] for e in evidence)})


if __name__ == "__main__":
    main(sys.argv[1])
