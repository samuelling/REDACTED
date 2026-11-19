// The grounds of REDACTED: trees grown in code (one template per species habit, instanced across the lawn),
// Washington globe lamps, and canvas textures for leaves and lit city windows.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
function rng(seed) { let s = seed | 0 || 1; return () => { s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// Habit of each kind of tree, at unit canopy radius. The HABS landscape plan gives each tree's species and spread.
// November in Washington: the elms and lindens are nearly bare, the oaks and beeches hold brown leaves, the magnolias stay green.
export const HABIT = {
  elm:      { h: 2.1, trunk: .30, split: 5, splitAt: .3, splitAngle: .5, levels: 4, kids: [5, 4, 4, 3], ang: [.42, .55, .7, .8], len: [.62, .62, .6, .55], arch: .32, leaf: .34, leafColor: 0x8a6d2c, leafSize: .05, bark: 0x51483e },
  oak:      { h: 1.6, trunk: .26, split: 4, splitAt: .28, splitAngle: .85, levels: 4, kids: [4, 4, 3, 3], ang: [.8, .75, .8, .8], len: [.68, .62, .6, .55], arch: .12, leaf: .7, leafColor: 0x6b4a26, leafSize: .05, bark: 0x4a4038 },
  linden:   { h: 2.5, trunk: .55, split: 6, splitAt: .3, splitAngle: .75, levels: 3, kids: [5, 4, 3], ang: [.8, .8, .8], len: [.55, .55, .5], arch: .18, leaf: .3, leafColor: 0x8c7a35, leafSize: .05, bark: 0x4d4741 },
  beech:    { h: 1.8, trunk: .18, split: 5, splitAt: .2, splitAngle: .7, levels: 4, kids: [4, 4, 3, 3], ang: [.75, .7, .75, .8], len: [.66, .62, .58, .55], arch: .2, leaf: .65, leafColor: 0x7d4a22, leafSize: .05, bark: 0x6d6a66 },
  magnolia: { h: 2.4, trunk: .5, split: 7, splitAt: .12, splitAngle: .5, levels: 3, kids: [4, 3, 3], ang: [.7, .8, .8], len: [.55, .55, .5], arch: .05, leaf: 1.7, leafColor: 0x22401f, leafSize: .075, bark: 0x4a4540, cone: true },
  small:    { h: 1.7, trunk: .2, split: 4, splitAt: .3, splitAngle: .8, levels: 3, kids: [4, 3, 3], ang: [.7, .75, .8], len: [.6, .6, .55], arch: .1, leaf: .2, leafColor: 0x6e2d22, leafSize: .06, bark: 0x4b423b },
};

// One tree, at canopy radius 1: { bark, leaves } geometries. Tubes along curved branches, leaf cards at the twigs.
export function growTree(kind, seed, lod = 1) {
  const H = HABIT[kind], r = rng(seed);
  const pos = [], nrm = [], uv = [], idx = [];
  const lp = [], ln = [], lu = [], li = [];
  const radial = (lvl) => Math.max(3, Math.round((lvl === 0 ? 8 : lvl === 1 ? 6 : lvl === 2 ? 5 : 3) * lod));
  const perp = (d) => { const a = Math.abs(d.y) < .9 ? V(0, 1, 0) : V(1, 0, 0); return new THREE.Vector3().crossVectors(d, a).normalize(); };
  function tube(pts, r0, r1, lvl) {
    const n = radial(lvl), base = pos.length / 3;
    let u = perp(pts[1].clone().sub(pts[0]).normalize());
    for (let i = 0; i < pts.length; i++) {
      const d = (i < pts.length - 1 ? pts[i + 1].clone().sub(pts[i]) : pts[i].clone().sub(pts[i - 1])).normalize();
      u = u.sub(d.clone().multiplyScalar(u.dot(d))).normalize(); const w = new THREE.Vector3().crossVectors(d, u);
      const rad = r0 + (r1 - r0) * i / (pts.length - 1);
      for (let k = 0; k <= n; k++) {
        const a = k / n * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
        const nx = u.x * c + w.x * s, ny = u.y * c + w.y * s, nz = u.z * c + w.z * s;
        pos.push(pts[i].x + nx * rad, pts[i].y + ny * rad, pts[i].z + nz * rad); nrm.push(nx, ny, nz); uv.push(k / n * Math.max(1, rad * 18), i * .6);
      }
    }
    for (let i = 0; i < pts.length - 1; i++) for (let k = 0; k < n; k++) { const a = base + i * (n + 1) + k, b = a + n + 1; idx.push(a, b, a + 1, a + 1, b, b + 1); }
  }
  function leafCards(at, dir, count, size) {
    for (let c = 0; c < count; c++) {
      const p = at.clone().add(V(r() - .5, r() - .5, r() - .5).multiplyScalar(size * 2.2)).add(dir.clone().multiplyScalar(size * r()));
      const n = V(r() - .5, r() * .6, r() - .5).normalize(), t = perp(n), b = new THREE.Vector3().crossVectors(n, t);
      const s = size * (.7 + r() * .6), base = lp.length / 3;
      for (const [x, y] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { const q = p.clone().add(t.clone().multiplyScalar(x * s)).add(b.clone().multiplyScalar(y * s)); lp.push(q.x, q.y, q.z); ln.push(n.x, Math.abs(n.y) + .4, n.z); lu.push((x + 1) / 2, (y + 1) / 2); }
      li.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  }
  const levels = Math.max(2, H.levels - (lod < .7 ? 1 : 0));
  const trunkH = H.h * H.splitAt, trunkR = H.trunk * .1 * (1 + H.h * .2);
  function branch(a, d, len, rad, lvl) {
    const segs = lvl === 0 ? 4 : lvl < 2 ? 3 : 2, pts = [a.clone()];
    let dir = d.clone();
    for (let i = 1; i <= segs; i++) {
      dir.add(V(r() - .5, r() - .5, r() - .5).multiplyScalar(.25 * (lvl ? 1 : .3)));
      dir.y -= H.arch * (lvl / levels) * .6; dir.y += (lvl === 0 ? .15 : .04);
      dir.normalize(); pts.push(pts[i - 1].clone().add(dir.clone().multiplyScalar(len / segs)));
    }
    const endR = lvl === levels ? rad * .25 : rad * .62;
    tube(pts, rad, endR, lvl);
    if (lvl >= levels) { if (H.leaf > 0) leafCards(pts[pts.length - 1], dir, Math.max(1, Math.round(H.leaf * 9 * (r() + .5))), H.leafSize); return; }
    const n = lvl === 0 ? H.split : H.kids[Math.min(lvl, H.kids.length - 1)];
    const golden = 2.399963;
    for (let k = 0; k < n; k++) {
      const t = lvl === 0 ? .9 + r() * .1 : .35 + .65 * (k + r() * .5) / n;
      const at = Math.min(segs - 1e-3, t * segs), i0 = Math.floor(at), f = at - i0;
      const p = pts[i0].clone().lerp(pts[i0 + 1], f);
      const ang = lvl === 0 ? H.splitAngle * (.8 + r() * .4) : H.ang[Math.min(lvl, H.ang.length - 1)] * (.75 + r() * .5);
      const axis = perp(dir).applyAxisAngle(dir, golden * k + r()); const cd = dir.clone().applyAxisAngle(axis, ang);
      if (H.cone) cd.y += .3 - lvl * .1;
      cd.normalize();
      const cl = (lvl === 0 ? H.h * (1 - H.splitAt) * .62 : len * H.len[Math.min(lvl, H.len.length - 1)]) * (.8 + r() * .4) * (lvl === 0 ? 1 : 1 - .35 * t);
      branch(p, cd, cl, rad * (lvl === 0 ? .55 : .6) * (.9 + r() * .2), lvl + 1);
    }
  }
  branch(V(0, 0, 0), V(0, 1, 0), trunkH, trunkR, 0);
  // fit: canopy radius 1
  const bark = new THREE.BufferGeometry(); bark.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); bark.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3)); bark.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); bark.setIndex(idx);
  let leaves = null;
  if (lp.length) { leaves = new THREE.BufferGeometry(); leaves.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3)); leaves.setAttribute('normal', new THREE.Float32BufferAttribute(ln, 3)); leaves.setAttribute('uv', new THREE.Float32BufferAttribute(lu, 2)); leaves.setIndex(li); }
  bark.computeBoundingBox(); const b = bark.boundingBox; const spread = Math.max(-b.min.x, b.max.x, -b.min.z, b.max.z) || 1;
  // canopy radius 1, and the habit's own height (crown height to spread, as grown trees of the kind stand)
  const k = 1 / spread, ky = H.h / Math.max(b.max.y, 1e-3); bark.scale(k, ky, k); if (leaves) leaves.scale(k, ky, k);
  bark.computeVertexNormals(); return { bark, leaves, height: H.h };
}

// A cluster of leaves on a transparent card.
export function leafTexture(seed = 3) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d'); const r = rng(seed);
  for (let i = 0; i < 9; i++) {
    x.save(); x.translate(20 + r() * 88, 20 + r() * 88); x.rotate(r() * 6.28);
    const l = 14 + r() * 16; const g = x.createLinearGradient(-l, 0, l, 0); const v = 150 + r() * 80;
    g.addColorStop(0, `rgb(${v},${v},${v})`); g.addColorStop(1, `rgb(${v * .8},${v * .8},${v * .8})`);
    x.fillStyle = g; x.beginPath(); x.ellipse(0, 0, l, l * .42, 0, 0, 7); x.fill(); x.restore();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// The Washington globe lamp: fluted post, collar, white globe. Base at y=0, unit = metres at the house's scale.
export function globeLamp(h = 5.2) {
  const post = new THREE.LatheGeometry([[.0, 0], [.32, 0], [.3, .25], [.2, .35], [.16, .5], [.1, h * .5], [.08, h - .5], [.14, h - .42], [.16, h - .3], [.0, h - .3]].map(([a, b]) => new THREE.Vector2(a, b)), 12);
  const globe = new THREE.SphereGeometry(.42, 18, 12).translate(0, h + .05, 0);
  const cap = new THREE.ConeGeometry(.12, .3, 10).translate(0, h + .55, 0);
  return { iron: mergeGeometries([post, cap]), globe };
}

// A soft round glow for lamps and lit windows seen from afar.
export function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  const g = x.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, 'rgba(255,230,180,1)'); g.addColorStop(.25, 'rgba(255,210,150,.45)'); g.addColorStop(1, 'rgba(255,200,140,0)');
  x.fillStyle = g; x.fillRect(0, 0, 64, 64); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// Window grid for far buildings: a façade texture with some windows lit, as an emissive map.
export function windowTexture(cols, rows, seed = 1, lit = .45) {
  const c = document.createElement('canvas'); c.width = cols * 16; c.height = rows * 24; const x = c.getContext('2d'); const r = rng(seed);
  x.fillStyle = '#000'; x.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
    if (r() > lit) continue; const v = 140 + r() * 115; x.fillStyle = `rgb(${v},${v * .82},${v * .55})`; x.fillRect(i * 16 + 4, j * 24 + 4, 8, 15);
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.LinearFilter; return t;
}

// Major plantings of the North Lawn, digitised from the HABS DC-37 landscape plan (sheet 3, "Identification of major
// plantings", 1992). Each entry: [x, y, species key, canopy radius] in pixels of the sheet's master scan reduced 4x and
// cropped at (195, 2670); north is down the sheet, east to the left. 2.52 px to the foot. The north facade is y=112,
// the centre line x=1050, the Pennsylvania Avenue fence y=800, the fountain (1050, 580).
export const NORTH_LAWN_TREES = [
  [215, 60, 'MG', 60], [105, 100, 'QH', 25], [105, 230, 'QH', 25], [105, 335, 'QH', 25], [105, 440, 'QH', 25], [105, 545, 'QH', 25], [105, 650, 'QH', 25], [105, 785, 'QH', 25],
  [395, 135, 'MA', 20], [390, 162, 'MA', 18], [375, 190, 'MA', 20], [500, 130, 'CC', 22], [455, 145, 'CC', 20], [440, 180, 'CF', 22], [460, 205, 'CF', 20], [490, 175, 'FA', 35],
  [590, 115, 'CF', 15], [612, 125, 'MS', 14], [650, 115, 'CP', 15], [690, 118, 'CP', 15], [740, 110, 'CP', 14], [785, 103, 'CP', 14], [590, 155, 'FA', 25], [660, 160, 'FA', 50], [770, 155, 'FA', 45],
  [190, 270, 'MI', 15], [255, 258, 'MI', 14], [180, 310, 'MI', 15], [220, 328, 'LT', 65], [365, 268, 'PC', 35], [460, 293, 'QA', 40], [700, 268, 'UA', 30], [600, 332, 'UA', 35],
  [380, 402, 'TU', 55], [505, 415, 'UA', 20], [205, 488, 'FP', 45], [335, 495, 'CL', 35], [440, 512, 'UA', 30], [240, 568, 'QP', 30], [315, 615, 'TU', 45], [400, 612, 'UA', 30], [255, 668, 'QP', 35],
  [670, 503, 'QB', 120], [860, 365, 'AP', 55], [862, 422, 'TU', 65], [590, 628, 'AH', 30], [730, 618, 'LT', 75], [860, 630, 'TU', 60], [575, 718, 'CH', 30], [360, 780, 'QC', 90], [270, 775, 'FS', 30],
  [620, 785, 'AP', 30], [660, 770, 'CF', 25], [840, 830, 'CF', 30], [965, 760, 'CF', 30], [190, 745, 'CF', 30], [460, 595, 'CF', 15],
  [1395, 160, 'FA', 40], [1520, 150, 'FA', 45], [1640, 155, 'FA', 55], [1775, 150, 'FA', 45], [1620, 238, 'QP', 30], [1750, 248, 'AO', 40], [1485, 272, 'UA', 90], [1770, 315, 'TC', 40], [1720, 345, 'TC', 45],
  [1280, 365, 'UA', 95], [1345, 398, 'UA', 50], [1280, 415, 'TU', 70], [1280, 470, 'TU', 45], [1635, 428, 'UA', 110], [1520, 578, 'UA', 100], [1280, 577, 'TU', 55], [1280, 630, 'TU', 50], [1420, 662, 'AH', 60],
  [1280, 732, 'TU', 45], [1385, 788, 'FP', 70], [1610, 740, 'QB', 25], [1760, 612, 'UA', 30], [1880, 262, 'UA', 35], [1955, 145, 'UP', 45], [2020, 175, 'QB', 20], [1950, 228, 'UA', 35], [2040, 270, 'QB', 20],
  [1950, 325, 'UA', 35], [2040, 350, 'QB', 20], [1950, 412, 'UA', 35], [2040, 460, 'QB', 15], [1955, 500, 'UA', 45], [1950, 577, 'UA', 95], [2030, 575, 'QB', 25], [1945, 755, 'QM', 85], [1880, 775, 'FY', 40], [1200, 755, 'CF', 25],
];
// Species key (HABS legend) to the habit it is grown with here.
export const KIND_OF = { UA: 'elm', UP: 'elm', QB: 'oak', QC: 'oak', QP: 'oak', QM: 'oak', QA: 'oak', QH: 'oak', TU: 'linden', TC: 'linden', LT: 'linden', FA: 'beech', FS: 'beech', FY: 'beech',
  MG: 'magnolia', AP: 'oak', AO: 'linden', AH: 'linden', FP: 'oak', PC: 'oak', CL: 'small', CH: 'small', MA: 'small', MS: 'small', CF: 'small', CP: 'small', CC: 'small', MI: 'small' };
export const COMMON = { UA: 'American elm', UP: 'English elm', QB: 'Northern red oak', QC: 'Scarlet oak', QP: 'Pin oak', QM: 'Bur oak', QA: 'White oak', QH: 'Willow oak', TU: 'European linden',
  TC: 'Little-leaf linden', LT: 'Tulip tree', FA: 'Fernleaf beech', FS: 'European beech', FY: 'Purple beech', MG: 'Southern magnolia', AP: 'Norway maple', AO: 'Yellow buckeye', AH: 'Horse chestnut',
  FP: 'Red ash', PC: 'American planetree', CL: 'American yellowwood', CH: 'Chinese redbud', MA: 'White saucer magnolia', MS: 'Star magnolia', CF: 'White flowering dogwood', CP: 'Washington hawthorn',
  CC: 'Cockspur hawthorn', MI: 'Bechtel crab apple' };
