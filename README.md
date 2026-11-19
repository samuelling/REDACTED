# REDACTED

A figure-ground piece built from the DOJ Epstein files. The FBI's search photographs
are moved, in shooting order, onto the public tour of a gilded White House. Every
mundane thing the photographs caught becomes an object in the rooms; every
photograph with no legible text hangs as an empty gilded frame. The people are the
one thing kept out: they stand in the rooms as matte black human shapes that take
no light, one for every 1,000 redactions in the release.

The voids stay voids. The piece never tries to fill in who was there.

Open `site/index.html` through any static server (or GitHub Pages pointed at
`site/`). Drag to look around, arrows or the buttons to move between rooms.

## How the rooms are filled

| What you see | Where it comes from |
| --- | --- |
| The tour | 13 rooms in public-tour order: Ground Floor Corridor, Library, Vermeil, China, Diplomatic Reception, East, Green, Blue, Red, State Dining, Cross Hall, Entrance Hall, Oval Office |
| Which photographs belong to a room | Data Set 1's 3,097 photographs split, in Bates order, into 13 equal stretches |
| Objects | Each photograph's OCR text matched against a lexicon of everyday objects (`scripts/build_inventory.py`); one object per mention |
| Empty frames | One per photograph whose OCR text is under 6 characters |
| Placard code | The FBI room placards that fall in that stretch |
| Black figures | Total redaction fragments in the release ÷ 1,000 (191), shared out by floor area. Counts only: no recovered text or names are read |

## Pipeline

```
pip install duckdb
npm i -g @gltf-transform/cli
python scripts/build_rooms.py documents-00000.parquet              # -> data/rooms.json (git-ignored)
python scripts/build_inventory.py recovered_redactions-00000.parquet  # -> site/inventory.json
python scripts/fetch_models.py /tmp/polyhaven                       # -> site/models/*.glb
```

Only object categories and counts reach `site/`. No OCR text, names or addresses
are published.

## Notes from the data

- Data Set 1 is FBI search photography, starting at the Manhattan townhouse
  (the first file is the photographer's log for 9 East 71st St).
- 61 room placards, codes A–Z and AA–NN, in the first ~1,370 files, in at least
  three passes rather than one walk through the house. The last ~1,790 files have
  no placards and lean toward Little St. James.
- Only 690 of 3,097 photographs carry legible text.
- Data Set 1 itself is barely redacted (7 pages), so the figures draw on the
  whole release.

## Credits

Data: [kabasshouse/epstein-data](https://huggingface.co/datasets/kabasshouse/epstein-data)
(CC-BY-4.0), OCR of the DOJ's Epstein Files Transparency Act release.

Public domain (CC0) models from [Poly Haven](https://polyhaven.com), resized and
recompressed: `cardboard_box_01`, `korean_fire_extinguisher_01`,
`lightbulb_01`, `Drill_01`, `ladder_sectioned_01`, `compost_bags`,
`book_encyclopedia_set_01`, `stationery_supplies`, `Barrel_01`, `metal_jerrycan`,
`filmstrip_projector_8mm`, `potted_plant_01`, `potted_plant_04`,
`multi_cleaner_5_litre`, `Chandelier_01`, `Chandelier_03`,
`ornate_mirror_01`, `marble_bust_01`, `ClassicConsole_01`, `dining_chair_02`.

Everything else (rooms, frames, figures, utility vehicles, network racks,
printers, the piano) is built in code. three.js 0.160 from jsDelivr.
