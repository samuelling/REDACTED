"""Rewrite each site/models/*.glb as a self-contained glTF JSON (site/models/*.json).

Artifact hosting serves .json but not .glb; three.js's GLTFLoader reads both.
"""
import base64
import json
import struct
from pathlib import Path

MODELS = Path(__file__).resolve().parent.parent / "site" / "models"

for glb in sorted(MODELS.glob("*.glb")):
    data = glb.read_bytes()
    magic, _, _ = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", glb
    off, doc, binary = 12, None, b""
    while off < len(data):
        length, kind = struct.unpack_from("<I4s", data, off)
        chunk = data[off + 8: off + 8 + length]
        if kind == b"JSON":
            doc = json.loads(chunk)
        elif kind == b"BIN\x00":
            binary = chunk
        off += 8 + length
    if doc.get("buffers"):
        doc["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binary).decode()
    out = glb.with_suffix(".json")
    out.write_text(json.dumps(doc, separators=(",", ":")))
    glb.unlink()
    print(f"{out.name:36s} {out.stat().st_size / 1024:8.0f} KB")
