# REDACTED

A figure-ground piece built from the DOJ Epstein files. Everything the government
released, the inventory of a house being taken apart room by room, is rendered as
the ground. The figure is never drawn. It shows up only as the space the camera
pointed around, and as the voids left by redaction.

The voids stay voids: the piece never tries to fill in who was there.

## Source

[`kabasshouse/epstein-data`](https://huggingface.co/datasets/kabasshouse/epstein-data)
(CC-BY-4.0), the OCR'd DOJ release. Data Set 1 (EFTA00000001–EFTA00003158) is the
FBI's search photography; it sits in `data/documents/documents-00000.parquet`.

## Pipeline

```
pip install duckdb
python scripts/build_rooms.py documents-00000.parquet   # -> data/rooms.json
```

`build_rooms.py` finds the FBI room placards ("B Search Personnel … Search
Completed") and assigns each following photo to that room until the next placard.

## What the first pass found

- 61 placards with room codes A–Z and AA–NN, roughly 8 photos per room, in the
  first ~1,370 files.
- The codes do not form one clean walk through the house. There are at least three
  passes, one ascending (B → KK), one that runs back down (G, F, E, …, A), and a
  later run on a different placard form ("Building No. / Description of Room").
- The last ~1,790 files have no placards and mention Little St. James more often,
  so they likely come from other properties or evidence handling.
- Only 690 of 3,097 photos carry legible text. Most frames are wordless.
- Floor mentions (Ground through 6th) appear throughout, so rooms might be
  placeable on floors with more work.
