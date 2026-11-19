"""Download CC0 models from Poly Haven and pack each as a small GLB for the web.

    python scripts/fetch_models.py RAW_DIR

Needs the glTF-Transform CLI (npm i -g @gltf-transform/cli). Writes
site/models/<id>.glb with textures resized to 512 px WebP, simplified and quantized (three.js reads this without a decoder).
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = [
    # inventory
    "cardboard_box_01", "korean_fire_extinguisher_01", "lightbulb_01",
    "Drill_01", "ladder_sectioned_01", "compost_bags", "book_encyclopedia_set_01",
    "stationery_supplies", "Barrel_01", "metal_jerrycan", "filmstrip_projector_8mm",
    "potted_plant_01", "potted_plant_04", "multi_cleaner_5_litre",
    # the rooms themselves
    "Chandelier_01", "Chandelier_03",
    "ornate_mirror_01", "marble_bust_01", "ClassicConsole_01", "dining_chair_02",
    "Sofa_01", "ArmChair_01", "metal_tool_chest", "throw_pillows_01", "vintage_grandfather_clock_01",
    "mantel_clock_01", "Television_01", "television_02", "security_camera_02",
    # fittings for the fictionalized rooms
    "steel_frame_shelves_01", "wooden_display_shelves_01", "electric_stove", "metal_office_desk",
    "cement_bag", "planter_box_01",
    # furnishing the rooms by type
    "GothicBed_01", "ClassicNightstand_01", "sofa_02", "coffee_table_round_01", "desk_lamp_arm_01",
    "steel_frame_shelves_02", "wooden_crate_01", "plastic_crate_01", "covered_car", "hand_truck", "tool_cart",
    "vintage_microwave", "drawer_cabinet", "binder_notebook", "portable_generator", "Shelf_01",
]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "redacted-art-project"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main(raw_dir: str) -> None:
    raw = Path(raw_dir)
    out = ROOT / "site" / "models"
    out.mkdir(parents=True, exist_ok=True)
    for mid in MODELS:
        glb = out / f"{mid}.glb"
        if glb.exists():
            continue
        files = json.loads(get(f"https://api.polyhaven.com/files/{mid}"))
        if "gltf" not in files:
            print(f"{mid:32s} no glTF download, skipped")
            continue
        entry = files["gltf"]["1k"]["gltf"]
        folder = raw / mid
        folder.mkdir(parents=True, exist_ok=True)
        gltf_path = folder / f"{mid}.gltf"
        gltf_path.write_bytes(get(entry["url"]))
        for rel, info in entry.get("include", {}).items():
            dest = folder / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(get(info["url"]))
        subprocess.run(
            ["gltf-transform", "optimize", str(gltf_path), str(glb),
             "--compress", "quantize", "--texture-compress", "webp", "--texture-size", "512",
             "--simplify-ratio", "0.35", "--simplify-error", "0.002"],
            check=True, capture_output=True,
        )
        print(f"{mid:32s} {glb.stat().st_size / 1024:8.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1])
