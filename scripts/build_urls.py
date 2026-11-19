"""Collect every web address that appears in the emails of the release.

    python scripts/build_urls.py        # -> site/computers/urls.json

Reads kabasshouse/epstein-data's documents table over HTTPS (DuckDB httpfs),
keeping only documents typed as email. Each address is reduced to host + path
(query strings and fragments, where names, emails and tokens live, are cut),
and any address with words that could refer to minors is withheld: it is kept
only as an entry saying so (with its count and source email), never as text.
The page shows addresses as plain text; none of them is ever a link.
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SHARDS = [f"hf://datasets/kabasshouse/epstein-data/data/documents/documents-{i:05d}.parquet" for i in range(15)]

URL = re.compile(r"(?:https?://|www\.)[^\s<>\"'()\[\]{}|\\^`]+", re.I)
HOST_OK = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,24}$")
# Anything that could point at minors is dropped, whatever the site.
MINORS = re.compile(r"teen|young|youth|lolit|loli\b|preteen|pre-teen|underage|under-age|child|kid|school|girl|boy|jailbait|minor|virgin|pthc|baby|tween|junior|little|petite|barely|cheerlead|student|daughter|niece|\b1[0-7]\b", re.I)


WITHHELD = "\x00withheld"


def clean(raw: str) -> str | None:
    u = raw.strip().rstrip(".,;:!?*>")
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.split(r"[?#]", u, 1)[0]
    if "@" in u or "=" in u:
        u = u.split("/", 1)[0]  # keep only the host when the path carries an address or a token
    host, _, path = u.partition("/")
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not HOST_OK.match(host) or ".." in host:
        return None
    segs = [s for s in path.split("/") if s]
    segs = ["…" if len(s) > 40 or re.fullmatch(r"[A-Za-z0-9_-]{24,}", s) else s for s in segs][:6]
    out = host + ("/" + "/".join(segs) if segs else "")
    if MINORS.search(out):
        import hashlib
        return WITHHELD + hashlib.sha1(out.encode()).hexdigest()[:10]  # distinct, but never readable
    return out


def main() -> None:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    counts, first, dropped, emails = Counter(), {}, 0, 0
    for shard in SHARDS:
        rows = con.execute(
            f"SELECT file_key, dataset, full_text FROM read_parquet('{shard}') "
            "WHERE document_type ILIKE '%mail%' AND full_text IS NOT NULL"
        ).fetchall()
        emails += len(rows)
        for key, dataset, text in rows:
            seen = set()
            for raw in URL.findall(text):
                u = clean(raw)
                if u is None:
                    dropped += 1
                    continue
                if u in seen:
                    continue
                seen.add(u)
                counts[u] += 1
                first.setdefault(u, (key, dataset))
        print(shard.rsplit("/", 1)[1], len(rows), "emails,", len(counts), "addresses so far", flush=True)

    out = ROOT / "site" / "computers"
    out.mkdir(parents=True, exist_ok=True)
    records = [[None if u.startswith(WITHHELD) else u, n, first[u][0], first[u][1]] for u, n in counts.most_common()]
    withheld = sum(1 for r in records if r[0] is None)
    (out / "urls.json").write_text(json.dumps({"emails": emails, "unreadable": dropped, "withheld": withheld, "urls": records}, separators=(",", ":")))
    hosts = Counter()
    for u, n in counts.items():
        if not u.startswith(WITHHELD):
            hosts[u.split("/", 1)[0]] += n
    print(f"{emails} emails, {len(records)} distinct addresses, {len(hosts)} sites, {withheld} withheld, {dropped} unreadable")
    print(hosts.most_common(25))


if __name__ == "__main__":
    main()
