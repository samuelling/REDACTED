"""Pack the screened photographs' enlargements into sheets (artifact hosting caps files per page).

    python scripts/build_photo_sheets.py     # reads site/photos/full/, writes site/photos/large-N.jpg

Each sheet holds 5 x 7 tiles of 400 x 292. site/photos/index.json gains "large": {EFTA: [sheet, col, row]}.
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "site" / "photos"
TW, TH, COLS, ROWS = 400, 292, 5, 7

idx = json.loads((P / "index.json").read_text())
large, sheet, k = {}, None, 0
nums = sorted(int(n) for n in idx["photos"])
for i, n in enumerate(nums):
    if i % (COLS * ROWS) == 0:
        if sheet:
            sheet.save(P / f"large-{k - 1}.jpg", quality=78, optimize=True)
        sheet = Image.new("RGB", (TW * COLS, TH * ROWS), (20, 18, 15)); k += 1
    im = Image.open(P / "full" / f"EFTA{n:08d}.jpg").convert("RGB")
    im.thumbnail((TW, TH))
    j = i % (COLS * ROWS)
    sheet.paste(im, ((j % COLS) * TW + (TW - im.width) // 2, (j // COLS) * TH + (TH - im.height) // 2))
    large[n] = [k - 1, j % COLS, j // COLS]
sheet.save(P / f"large-{k - 1}.jpg", quality=78, optimize=True)
idx["large"] = large; idx["large_tile"] = [TW, TH, COLS, ROWS]
(P / "index.json").write_text(json.dumps(idx, separators=(",", ":")))
print(len(large), "photographs on", k, "sheets")
