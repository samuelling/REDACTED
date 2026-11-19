"""Turn the search photos' OCR text into an inventory of mundane objects.

Reads data/rooms.json (from build_rooms.py), matches each photo's text against
an object lexicon, and maps the FBI's shooting order onto the White House tour
route: the photos are split, in order, into one block per tour room.

Output: site/inventory.json
    {"objects": {category: total},
     "rooms": [{"id", "efta_start", "efta_end", "photos", "wordless", "objects": {category: n}}]}

Only object categories and counts leave this script. No OCR text, names or
addresses are written out.
"""

import json
import sys
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# category -> trigger patterns (matched case-insensitively against one photo's text)
LEXICON = {
    "storage_box":   [r"\bZORRO\b", r"\bMISC\b", r"\bLSJ\b", r"\bPARIS\b", r"FAMILY PHOTOS", r"\bFILES?\b", r"BOOK \d"],
    "shipping_box":  [r"FEDEX", r"\bULINE\b", r"\bUPS\b", r"THIS SIDE UP", r"FRAGILE", r"SHIP TO"],
    "fire_extinguisher": [r"EXTINGUISHER", r"PULL PIN", r"AMEREX", r"FIREGUARD"],
    "exit_sign":     [r"\bEXIT\b"],
    "warning_sign":  [r"DANGER", r"CAUTION", r"WARNING", r"NO SMOKING", r"HIGH VOLTAGE", r"\bNOTICE\b"],
    "keep_calm_poster": [r"KEEP CALM"],
    "network_switch": [r"UNIFI", r"CISCO", r"ROUTER", r"FIREWALL", r"NETGEAR", r"\bAPC\b", r"FIRMWARE", r"\bSWITCH\b"],
    "pipe_valve":    [r"HEATING WATER", r"CHILLED WATER", r"SIEMENS", r"APOGEE", r"\bVALVE", r"\bDRAIN\b", r"WATER MAIN", r"\bPRESSURE\b"],
    "lightbulb":     [r"PHILIPS", r"SUNLITE", r"HALOGEN", r"\bBULBS?\b", r"\bLED\b", r"LIGHT MASTER"],
    "power_tool":    [r"RIDGID", r"RYOBI", r"HUSKY", r"DEWALT", r"MILWAUKEE", r"MAKITA", r"\bTOOLS?\b"],
    "ladder":        [r"WERNER", r"LITTLE GIANT", r"LADDER"],
    "potting_soil":  [r"FAFARD", r"POTTING", r"COMPOST", r"\bSOIL\b", r"\bMULCH\b"],
    "boxing_gloves": [r"EVERLAST", r"\bTKO\b", r"\bGLOVES\b", r"HAND WRAPS"],
    "exercise_gear": [r"CYBEX", r"WEIGHTS?\b", r"JUMP ROPE", r"EXERCISE", r"FITNESS"],
    "printer":       [r"EPSON", r"BROTHER", r"CARTRIDGE", r"PRINTER", r"\bINK\b"],
    "books":         [r"\bBOOK\b", r"TASCHEN", r"COOKBOOK", r"FIRE AND FURY", r"TOEFL", r"DICTIONARY", r"PHILOSOPH"],
    "tissue_box":    [r"KLEENEX", r"TISSUE", r"SPARKLE"],
    "water_bottle":  [r"\bVOSS\b", r"EVIAN", r"FIJI", r"POLAND SPRING"],
    "office_supplies": [r"ENVELOPES?", r"STAPLER", r"\bPENS\b", r"PENCILS", r"MARKERS", r"PAPER CLIPS", r"STATIONARY|STATIONERY", r"LABEL MAKER"],
    "fuel_drum":     [r"DIESEL", r"\bFUEL\b", r"\bOIL\b", r"GASOLINE", r"\bTANK\b", r"PROPANE"],
    "utility_vehicle": [r"JOHN DEERE", r"POLARIS", r"RANGER", r"KAWASAKI", r"WAVERUNNER", r"\bCAT\b", r"YAMAHA", r"GOLF CART"],
    "grand_piano":   [r"STEINWAY"],
    "security_camera": [r"SURVEILLANCE", r"\bCCTV\b", r"\bCAMERA\b"],
    "slide_projector": [r"KODAK", r"PROJECTOR"],
    "disc":          [r"\bDVD\b", r"\bCD\b", r"\bDISC\b", r"BLU-?RAY"],
    "desktop_computer": [r"\bAPPLE\b", r"\bIMAC\b", r"MACBOOK", r"A1419", r"LOGITECH", r"\bDELL\b"],
    "air_filter":    [r"FILTER"],
    "bed_linens":    [r"LINENS?", r"PILLOWS?", r"BATHROBES?", r"TOWELS?"],
    "skincare":      [r"SERUM", r"RETINOL", r"CLINIQUE", r"PETER ?THOMAS ?ROTH", r"MASSAGE", r"LOTION"],
    "laundry":       [r"IRONER", r"DETERGENT", r"\bTIDE\b", r"DRYER", r"WASHER"],
    "potted_plant":  [r"\bPLANTS?\b", r"ORCHID", r"\bPOTS\b"],
    "telephone":     [r"PANASONIC", r"\bPHONE\b", r"CORDLESS"],
}
COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in LEXICON.items()}

# The current White House public-tour order, then the Oval Office.
TOUR = [
    "ground_corridor", "library", "vermeil_room", "china_room", "diplomatic_reception_room",
    "east_room", "green_room", "blue_room", "red_room", "state_dining_room",
    "cross_hall", "entrance_hall", "oval_office",
]

PLACARD = re.compile(r"Search (Personnel|Warrant|Completed|Process)|Batch Process|Description of Room")


def objects_in(text: str) -> list[tuple[str, str]]:
    """(category, the word that matched) for each object category the text mentions."""
    found = []
    for cat, pats in COMPILED.items():
        for p in pats:
            m = p.search(text)
            if m:
                found.append((cat, m.group(0).upper()))
                break
    return found


# Frames: how each wordless photograph is shown, decided from the dataset's scene description.
PEOPLE = re.compile(r"\b(person|persons|people|man|men|woman|women|girl|girls|boy|boys|child|children|kid|kids|teen|teenager|baby|infant|individual|individuals|someone|figure|figures|silhouette|body|bodies|face|faces|torso|skin)\b", re.I)
SEXUAL = re.compile(r"\b(nude|naked|nudity|topless|undressed|breast|breasts|buttocks|genital|genitals|sex|sexual|erotic|explicit|pornographic|lingerie)\b", re.I)
# A person scene's description is shown only if it says nothing about youth, undress or beds.
SENSITIVE = re.compile(r"\b(girl|girls|boy|boys|child|children|kid|kids|teen|teenager|young|youth|minor|baby|infant|school|swimsuit|bikini|bathing|underwear|towel|robe|bed|beds|bedroom|bath|bathtub|shower|massage|lying|asleep|sleeping)\b", re.I)


def frame_record(efta: int, notes: str) -> list:
    """[EFTA, status, description]. status: photo | person | nudity | unknown."""
    notes = (notes or "").strip()
    if len(notes) < 40:
        return [efta, "unknown", ""]
    if SEXUAL.search(notes):
        return [efta, "nudity", ""]          # never described
    short = notes if len(notes) <= 300 else notes[:297].rsplit(" ", 1)[0] + "…"
    if PEOPLE.search(notes):
        return [efta, "person", "" if SENSITIVE.search(notes) else short]
    return [efta, "photo", short]


# What the scene descriptions say about the spaces themselves; used to fictionalize each room.
FEATURES = {
    "carpet": r"carpet", "tile": r"\btil(e|ed|es)\b", "concrete": r"concrete", "marble": r"marble",
    "wood_floor": r"(wood(en)?|hardwood|parquet) (floor|flooring)", "panel": r"panel(l)?ing|panel(l)?ed",
    "shelves": r"shel(f|ves|ving)|bookcase|bookshel", "storage": r"storage|boxes|stacked", "pipes": r"\bpipes?\b|duct|valve|boiler|mechanical|electrical panel|breaker",
    "construction": r"construction|renovation|unfinished|exposed (studs|joists|beams)|drywall|plywood",
    "outdoor": r"outdoor|palm|coast|beach|\bsea\b|ocean|garden|lawn", "kitchen": r"kitchen|refrigerator|stove|oven",
    "office": r"\boffice\b|\bdesk\b", "mirror": r"mirror", "closet": r"closet|wardrobe",
}
FEATURES = {k: re.compile(v, re.I) for k, v in FEATURES.items()}


def scene_notes(parquet: str | None) -> dict[int, str]:
    if not parquet:
        return {}
    import duckdb
    rows = duckdb.sql(f"SELECT file_key, additional_notes FROM read_parquet('{parquet}') WHERE dataset = 'DataSet1'").fetchall()
    return {int(re.sub(r"\D", "", k)): n or "" for k, n in rows}


def redaction_fragments(parquet: str | None) -> int | None:
    """Total redaction fragments across the release. Reads the count column only."""
    if not parquet:
        return None
    import duckdb
    return int(duckdb.sql(f"SELECT sum(num_fragments) FROM read_parquet('{parquet}')").fetchall()[0][0])


def main() -> None:
    redactions = redaction_fragments(sys.argv[1] if len(sys.argv) > 1 else None)
    notes = scene_notes(sys.argv[2] if len(sys.argv) > 2 else None)
    segments = json.loads((ROOT / "data" / "rooms.json").read_text())
    photos = [p for s in segments for p in s["photos"]]
    photos.sort(key=lambda p: p["efta"])

    n = len(TOUR)
    size = len(photos) / n
    rooms, totals = [], Counter()
    for i, room in enumerate(TOUR):
        block = photos[round(i * size): round((i + 1) * size)]
        counts, wordless, items, frames = Counter(), 0, [], []
        for p in block:
            text = p["text"]
            if len(text) < 6:
                wordless += 1
                frames.append(frame_record(p["efta"], notes.get(p["efta"], "")))
                continue
            if len(text) > 400 or PLACARD.search(text):  # documents and placards aren't objects
                continue
            for cat, term in objects_in(text):
                counts[cat] += 1
                items.append([cat, p["efta"], term])
        totals.update(counts)
        lo, hi = block[0]["efta"], block[-1]["efta"]
        described = [notes[p["efta"]] for p in block if notes.get(p["efta"])]
        features = {k: round(sum(1 for n in described if rx.search(n)) / max(1, len(described)), 3) for k, rx in FEATURES.items()}
        placards = [s["label"] for s in segments
                    if s["label"] not in ("?", "pre") and lo <= s["efta_start"] <= hi]
        rooms.append({
            "id": room,
            "efta_start": lo,
            "efta_end": hi,
            "photos": len(block),
            "wordless": wordless,
            "placards": placards,
            "features": features,  # share of described photographs mentioning each kind of space
            "objects": dict(counts.most_common()),
            "items": items,     # [category, EFTA number, matched word]
            "frames": frames,   # [EFTA, photo|person|nudity|unknown, scene description or ""]
        })

    out = ROOT / "site" / "inventory.json"
    out.parent.mkdir(exist_ok=True)
    status = Counter(f[1] for r in rooms for f in r["frames"])
    print("frames:", dict(status))
    out.write_text(json.dumps({
        "redaction_fragments": redactions,
        "objects": dict(totals.most_common()),
        "rooms": rooms,
    }, separators=(",", ":")))

    print(f"{sum(totals.values())} object mentions in {len(photos)} photos -> {out}")
    print(dict(totals.most_common()))
    for r in rooms:
        print(f'{r["id"]:>26} EFTA {r["efta_start"]:>5}-{r["efta_end"]:<5} wordless {r["wordless"]:3d}  {r["objects"]}')


if __name__ == "__main__":
    main()
