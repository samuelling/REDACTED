"""How many of the redacted people are women, how many men, how many unknown.

    python scripts/build_figures.py REDACTIONS_PARQUET      # -> site/figures/sexes.json

Only what the release leaves readable is used. For each page with redactions, the page's public
OCR text is searched for an honorific whose name has been removed ("Ms. , who", "Mr. and") and
for the stand-in names the files use ("Jane Doe", "John Doe", "Minor Victim"). Pages with no such
sign fall back on the document type: the victims who gave statements in this case are women and
girls, so redactions in victim statements count as female; anything else stays unknown.
The redactions table's recovered text and names columns are never read.
"""

import json
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SHARDS = [f"hf://datasets/kabasshouse/epstein-data/data/documents/documents-{i:05d}.parquet" for i in range(15)]
# An honorific followed by something other than a name: the name was blacked out.
GAP = r"(?:\.|\b)\s*(?=[,;:)\-–—]|\s+(?:and|or|who|was|is|had|has|said|told|to|of|in|at|on|with|from|by|for|\(|\[|$)|$)"
FEMALE = re.compile(r"\b(?:Ms|Mrs|Miss)" + GAP + r"|\bJane Doe\b|\bMinor Victim\b|\bVictim[- ]?\d+\b", re.M)
MALE = re.compile(r"\bMr" + GAP + r"|\bJohn Doe\b", re.M)


def main(redactions: str) -> None:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"CREATE TABLE r AS SELECT file_key, page_number, num_fragments, document_type FROM read_parquet('{redactions}')")
    pages = {(k, int(p)): (n, t) for k, p, n, t in con.execute("SELECT file_key, page_number, num_fragments, document_type FROM r").fetchall()}
    keys = sorted({k for k, _ in pages})
    con.execute("CREATE TABLE keys AS SELECT unnest(?) AS file_key", [keys])
    tally = {"female": 0, "male": 0, "unknown": 0}
    seen = set()
    for i, shard in enumerate(SHARDS):
        rows = con.execute(
            f"SELECT d.file_key, d.page_number, d.full_text FROM read_parquet('{shard}') d JOIN keys USING (file_key)"
        ).fetchall()
        for key, page, text in rows:
            try:
                p = int(page or 1)
            except ValueError:
                continue
            if (key, p) not in pages or (key, p) in seen:
                continue
            seen.add((key, p))
            n, dtype = pages[(key, p)]
            f, m = len(FEMALE.findall(text or "")), len(MALE.findall(text or ""))
            if f + m:
                tally["female"] += n * f / (f + m); tally["male"] += n * m / (f + m)
            elif dtype == "VICTIM_STATEMENT":
                tally["female"] += n
            else:
                tally["unknown"] += n
        print(f"shard {i}: {len(seen)} pages matched", flush=True)
    for (key, p), (n, dtype) in pages.items():  # pages whose text is not in the documents table
        if (key, p) not in seen:
            tally["female" if dtype == "VICTIM_STATEMENT" else "unknown"] += n
    out = {k: round(v) for k, v in tally.items()}
    out["pages"] = len(pages); out["pages_with_text"] = len(seen)
    out["method"] = "Honorifics with the name removed and stand-in names on each redacted page's public text; victim statements count as female; the rest unknown."
    (ROOT / "site" / "figures" / "sexes.json").write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
