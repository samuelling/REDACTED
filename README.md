# REDACTED

A figure-ground piece built from the DOJ Epstein files. The release is so heavily
redacted that mostly ground is left: rooms, objects, paperwork. This gallery is a
comprehensive collection of that ground, arranged in a gilded, enlarged White
House. The people appear only as matte black figures that take no light.

Open `site/index.html` through any static server (or GitHub Pages pointed at
`site/`). Visitors confirm they are 18 or over, start on the North Lawn, and walk
in through the North Portico. WASD and mouse on desktop, twin thumbs on a phone,
and a guided tour.

## How the gallery is arranged

Everything is placed by what it is, not by shooting order. Each object still
carries its photograph's EFTA number, the word that matched, and its position in
the FBI's shooting order (click it).

| Room | Holds |
| --- | --- |
| East Wing Ballroom (a Hall of Mirrors where the East Wing stood) | Storage shelving with the banker's and shipping boxes, fuel drums on pallets, the utility vehicles in rows, garden supplies |
| Oval Office | Offices: desks with the computers, phones and papers, printers, Keep Calm posters, the evidence tables |
| Situation Room | Network racks and a wall of monitors |
| East Room | Sitting rooms: sofas, televisions, DVDs, projectors, the pianos |
| Green Room | Kitchens and pantries |
| Blue Room | The gym |
| Red Room | Bedrooms |
| State Dining Room | Mechanical rooms: the pipe manifold, workbenches and power tools, ladders |
| Library, Vermeil, China, Diplomatic Reception and Map Rooms, the Vault | Library, bathrooms, laundry and linens, closets, massage rooms, safes |

Photographs hang in the room their scene description matches. Halls and stairs
take the corridor photographs.

## What is shown and what is withheld

- **Objects** come from OCR text matched against a lexicon of everyday things
  (`scripts/build_inventory.py`).
- **Photographs**: each wordless photograph is classified from the dataset's scene
  description. Any that describe a person hang as black frames tagged *Withheld:
  shows a person* (the description is shown on click unless it mentions youth,
  undress or beds). Any that describe nudity hang black, tagged *Withheld:
  nudity*, and are never described. Only screened photographs are ever fetched,
  and `scripts/build_photos.py` runs NudeNet and OpenCV's people detector over
  them before use; anything flagged stays black.
- **Black figures**: one per 1,000 redaction fragments in the release (191). They walk
  slowly about their rooms, stop and stand, or sit at the desks. Each is a woman, a man or,
  where the files do not say, a body halfway between the two, in proportion to what the
  readable text gives (`scripts/build_figures.py`): an honorific left standing beside a
  blacked-out name, a stand-in name ("Jane Doe", "Minor Victim"), or a victim statement
  (the victims in this case were women and girls). That comes to 6 women, no men and 185
  unknown: the release almost never says. Nothing beneath a redaction is read; the
  redactions table's recovered-text and names columns are never opened.
- **Evidence**: the 112 items in the FBI evidence-recovery log appear as sealed,
  tagged bags in the room where they were found. Item types only; adult items,
  photographs and personal papers are sealed in black bags and not described.
- **Computers**: every desktop computer opens a browser history of all 26,318 web
  addresses in the 689,073 emails of the release (`scripts/build_urls.py`). Query
  strings are cut, addresses are text and never links, and 1,458 addresses whose
  words could refer to minors are withheld and labelled as such.
- **Figure Mode** drops the ground: only the redacted people and the seized
  evidence remain.

## Pipeline

```
pip install duckdb pymupdf nudenet opencv-python-headless
npm i -g @gltf-transform/cli
python scripts/build_rooms.py documents-00000.parquet
python scripts/build_inventory.py recovered_redactions-00000.parquet documents-00000.parquet
python scripts/build_gallery.py documents-00000.parquet     # -> site/gallery.json
python scripts/build_urls.py                                 # -> site/computers/urls.json
python scripts/fetch_models.py /tmp/polyhaven && python scripts/glb_to_json.py
python scripts/fetch_surfaces.py
python scripts/build_photos.py PDF_DIR                       # screened photographs only
```

## Credits

Data: [kabasshouse/epstein-data](https://huggingface.co/datasets/kabasshouse/epstein-data)
(CC-BY-4.0), OCR and scene descriptions of the DOJ's Epstein Files Transparency Act release.

Architecture: built in code (`site/arch.js`) to the Historic American Buildings Survey
measured drawings of the White House, [HABS DC-37](https://www.loc.gov/item/dc0402/)
(Library of Congress, public domain): the first-floor plan, the north elevations, the North
Portico column and entablature (sheet 76), the typical first-floor windows (sheet 82) and the
north entrance (sheet 79). Every surveyed dimension is kept and scaled by the same factor as
the enlarged rooms.

Motion capture: [CMU Graphics Lab Motion Capture Database](http://mocap.cs.cmu.edu) (free for
research and commercial use), BVH conversion by Bruce Hahne via
[meshula/cmu-mocap](https://github.com/meshula/cmu-mocap). Bodies: the Blender Studio Human Base
Meshes bundle (CC0).

Models, surfaces and the ballroom HDRI: [Poly Haven](https://polyhaven.com) (CC0),
resized and recompressed; the model list is in `scripts/fetch_models.py`. Everything
else is built in code. three.js 0.160 from jsDelivr.

## Photographs and figures (added)

- `scripts/build_photos.py` + `scripts/build_photo_sheets.py`: the 1,731 photographs
  whose descriptions passed the text screen were fetched from justice.gov after the
  site's age check, run through NudeNet and OpenCV's people detector (315 flagged and
  withheld), and the remaining 1,416 packed into thumbnail and enlargement sheets in
  `site/photos/`. No one viewed them during processing.
- `scripts/rig_figures.py` (run with Blender's Python): the redacted figures are the
  Blender Studio Human Base Meshes (CC0, realistic male and female, plus their average),
  rigged with the motion-capture skeleton and driven by the CMU Graphics Lab Motion
  Capture Database (Bruce Hahne's BVH conversion): 07_04 slow walk, 77_02 standing and
  114_05 sitting in a chair. One stride is cut from the walk and run in place, and the
  page moves each figure at the stride's own speed so the feet do not slide.
  (`scripts/pose_figures.py`, the earlier static poses, is no longer used.)

## The architecture kit (`site/arch.js`)

Classical mouldings are drawn as profiles (fillets, ovolos, cavettos, cymas, tori, scotias)
and swept along the walls, so cornices, bases, chair rails, architraves and pediments are
curved, with crisp corners. Columns are turned with entasis, with Attic bases and Doric,
Ionic (four angled volutes and festoons, as at the North Portico) or Corinthian capitals.
Pilasters are fluted, ceilings are coffered or panelled, and windows have deep reveals with
panelled linings, glazing bars, curtains and swagged pelmets.

The Entrance Hall's diagonal checkerboard floor, the veined marble of the halls and the
boiserie and chimneypieces of the state rooms follow 3D Warehouse models of those rooms,
used for reference only. None of their geometry is published here.
