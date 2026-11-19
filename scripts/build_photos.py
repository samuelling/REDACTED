"""Turn the screened Data Set 1 photographs into frame textures.

    python scripts/build_photos.py PDF_DIR

Only photographs whose scene description passed the text screen (no people,
no nudity) are expected in PDF_DIR, as EFTA########.pdf. Each one is also run
through NudeNet (faces and body parts) and OpenCV's people detector; anything either flags is
not used and its frame stays black, tagged as withheld.

Writes:
  site/photos/atlas-N.jpg   thumbnails packed into 2048-px sheets (96 x 72 each)
  site/photos/full/EFTA########.jpg   a 960-px copy, loaded only when a frame is clicked
  site/photos/index.json    {EFTA: [sheet, column, row]} plus the list of rejected EFTA numbers
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TW, TH, SHEET = 96, 72, 2048
COLS, ROWS = SHEET // TW, SHEET // TH


def first_image(pdf: Path):
    import fitz  # PyMuPDF
    from PIL import Image
    doc = fitz.open(pdf)
    page = doc[0]
    pix = page.get_pixmap(dpi=110)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def main(pdf_dir: str) -> None:
    from PIL import Image
    import cv2
    from nudenet import NudeDetector

    # NudeNet finds faces and body parts, clothed or not; any of them means a person is in the frame.
    body = NudeDetector()
    hog = cv2.HOGDescriptor(); hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    out = ROOT / "site" / "photos"
    (out / "full").mkdir(parents=True, exist_ok=True)
    index, rejected, sheets, slot = {}, [], [], 0
    for pdf in sorted(Path(pdf_dir).glob("EFTA*.pdf")):
        n = int(pdf.stem[4:])
        img = first_image(pdf)
        tmp = out / "_check.jpg"
        img.save(tmp, quality=85)
        parts = [d for d in body.detect(str(tmp)) if d["score"] > 0.2]
        small = cv2.resize(cv2.imread(str(tmp)), (640, int(640 * img.height / img.width)))
        rects, weights = hog.detectMultiScale(small, winStride=(8, 8))
        tmp.unlink()
        if parts or any(float(w) > 0.6 for w in weights):
            rejected.append(n)
            continue
        full = img.copy(); full.thumbnail((960, 960)); full.save(out / "full" / f"EFTA{n:08d}.jpg", quality=78)
        if slot % (COLS * ROWS) == 0:
            sheets.append(Image.new("RGB", (SHEET, SHEET), (20, 18, 15)))
        k = slot % (COLS * ROWS)
        thumb = img.copy(); thumb.thumbnail((TW * 2, TH * 2))
        thumb = thumb.resize((TW, TH))
        sheets[-1].paste(thumb, ((k % COLS) * TW, (k // COLS) * TH))
        index[n] = [len(sheets) - 1, k % COLS, k // COLS]
        slot += 1
    for i, sh in enumerate(sheets):
        sh.save(out / f"atlas-{i}.jpg", quality=80)
    (out / "index.json").write_text(json.dumps({"tile": [TW, TH], "sheet": SHEET, "photos": index, "rejected": rejected}))
    print(f"{len(index)} photographs framed, {len(rejected)} rejected by the detectors, {len(sheets)} sheets")


if __name__ == "__main__":
    main(sys.argv[1])
