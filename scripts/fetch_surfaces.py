"""Download CC0 surfaces and the environment HDRI from Poly Haven.

    python scripts/fetch_surfaces.py

Writes site/tex/<id>_{diff,nor,arm}.jpg (1k) and site/env/ballroom.json, the
1k .hdr wrapped in JSON as base64 (artifact hosting serves .json, not .hdr).
"""

import base64
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SURFACES = [
    "herringbone_parquet", "marble_tiles", "painted_plaster_wall", "quatrefoil_jacquard_fabric",
    "poly_wool_herringbone", "dark_paneled_wood", "concrete_floor_worn_001", "large_floor_tiles_02", "long_white_tiles", "plywood",
    # the grounds
    "leafy_grass", "asphalt_02", "rectangular_paving", "bark_brown_02", "granite_tile",
]
MAPS = {"Diffuse": "diff", "nor_gl": "nor", "arm": "arm"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "redacted-art-project"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> None:
    tex = ROOT / "site" / "tex"
    tex.mkdir(parents=True, exist_ok=True)
    for sid in SURFACES:
        files = json.loads(get(f"https://api.polyhaven.com/files/{sid}"))
        for key, short in MAPS.items():
            out = tex / f"{sid}_{short}.jpg"
            if not out.exists():
                out.write_bytes(get(files[key]["1k"]["jpg"]["url"]))
        print(sid)
    env = ROOT / "site" / "env"
    env.mkdir(parents=True, exist_ok=True)
    files = json.loads(get("https://api.polyhaven.com/files/ballroom"))
    hdr = get(files["hdri"]["1k"]["hdr"]["url"])
    (env / "ballroom.json").write_text(json.dumps({"format": "hdr", "base64": base64.b64encode(hdr).decode()}))
    print("ballroom HDRI", len(hdr) // 1024, "KB")
    # The night sky over the grounds: Kloppenheim 07 (pure sky), tonemapped, upper hemisphere and a band below the horizon.
    from io import BytesIO
    from PIL import Image
    files = json.loads(get("https://api.polyhaven.com/files/kloppenheim_07_puresky"))
    im = Image.open(BytesIO(get(files["tonemapped"]["url"]))).convert("RGB")
    im = im.resize((4096, 2048), Image.LANCZOS).crop((0, 0, 4096, 1152))
    im.save(env / "sky.jpg", quality=86)
    print("sky", (env / "sky.jpg").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
