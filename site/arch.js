// Architectural kit for REDACTED: classical mouldings swept along paths, turned and fluted columns,
// capitals, balusters, coffers, windows and doors. Proportions follow the Historic American Buildings
// Survey drawings of the White House (HABS DC-37, Library of Congress, public domain).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const Y = new THREE.Vector3(0, 1, 0);
const TAU = Math.PI * 2, H = Math.PI / 2;
export const V = (x, y, z) => new THREE.Vector3(x, y, z);
export function clean(g) {
  g = g.index ? g.toNonIndexed() : g;
  for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
  if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
  if (!g.attributes.normal) g.computeVertexNormals();
  return g;
}
export const merge = (list) => { list = list.filter(Boolean); return list.length ? mergeGeometries(list.map(clean)) : null; };
export const M4 = (x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) =>
  new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz)), new THREE.Vector3(sx, sy, sz));
const bx = (w, h, d, x, y, z) => new THREE.BoxGeometry(w, h, d).translate(x, y, z);
export const box3 = bx;

// ---------------------------------------------------------------- profiles
// A profile is drawn in (s, t): s away from the backing surface, t along it. It starts on the backing at
// the bottom, works out and up through the mouldings, and ends back on the backing at the top.
export class Profile {
  constructor(s = 0, t = 0) { this.pts = [[s, t]]; this.sharp = [true]; }
  get last() { return this.pts[this.pts.length - 1]; }
  push(s, t, sharp) { const [a, b] = this.last; if (Math.hypot(s - a, t - b) < 1e-6) { if (sharp) this.sharp[this.sharp.length - 1] = true; return this; } this.pts.push([s, t]); this.sharp.push(!!sharp); return this; }
  mark() { this.sharp[this.sharp.length - 1] = true; return this; }
  to(s, t) { return this.mark().push(s, t, true); }
  up(h) { const [s, t] = this.last; return this.to(s, t + h); }
  out(w) { const [s, t] = this.last; return this.to(s + w, t); }
  fillet(w, h) { return this.out(w).up(h); }
  curve(w, h, f, n = 6) { this.mark(); const [s0, t0] = this.last; for (let i = 1; i <= n; i++) { const [a, b] = f(i / n); this.push(s0 + w * a, t0 + h * b, i === n); } return this; }
  ovolo(w, h, n) { return this.curve(w, h, (u) => [Math.sin(u * H), 1 - Math.cos(u * H)], n); }      // convex quarter round
  cove(w, h, n) { return this.curve(w, h, (u) => [1 - Math.cos(u * H), Math.sin(u * H)], n); }       // concave quarter (cavetto)
  cymaRecta(w, h, n = 8) { return this.curve(w, h, (u) => [(1 - Math.cos(Math.PI * u)) / 2, u], n); } // concave below, convex above
  cymaReversa(w, h, n = 8) { return this.curve(w, h, (u) => [u, (1 - Math.cos(Math.PI * u)) / 2], n); } // convex below, concave above
  torus(r, n = 8) { return this.curve(r, 2 * r, (u) => [Math.sin(Math.PI * u), 1 - Math.cos(Math.PI * u)], n); }
  scotia(r, n = 8) { return this.curve(-r, 2 * r, (u) => [Math.sin(Math.PI * u), 1 - Math.cos(Math.PI * u)], n); }
  back() { const [, t] = this.last; return this.to(this.pts[0][0], t); }
  scaled(ks, kt = ks) { const p = new Profile(); p.pts = this.pts.map(([s, t]) => [s * ks, t * kt]); p.sharp = this.sharp.slice(); return p; }
  moved(ds, dt) { const p = new Profile(); p.pts = this.pts.map(([s, t]) => [s + ds, t + dt]); p.sharp = this.sharp.slice(); return p; }
  swapped() { const p = new Profile(); p.pts = this.pts.map(([s, t]) => [t, s]); p.sharp = this.sharp.slice(); return p; }
  get height() { return Math.max(...this.pts.map((p) => p[1])) - Math.min(...this.pts.map((p) => p[1])); }
  get depth() { return Math.max(...this.pts.map((p) => p[0])); }
  // Vertices with outward normals; sharp corners are split so they shade crisply.
  entries() {
    const P = this.pts, m = P.length;
    let area = 0; for (let i = 0; i < m; i++) { const [a, b] = P[i], [c, d] = P[(i + 1) % m]; area += a * d - c * b; }
    const sg = area >= 0 ? 1 : -1;
    const nrm = []; for (let k = 0; k < m - 1; k++) { const ds = P[k + 1][0] - P[k][0], dt = P[k + 1][1] - P[k][1], l = Math.hypot(ds, dt) || 1; nrm.push([sg * dt / l, -sg * ds / l]); }
    const out = []; let v = 0;
    for (let k = 0; k < m; k++) {
      if (k > 0) v += Math.hypot(P[k][0] - P[k - 1][0], P[k][1] - P[k - 1][1]);
      const [s, t] = P[k];
      if (k === 0) out.push({ s, t, n: nrm[0], v, join: true });
      else if (k === m - 1) out.push({ s, t, n: nrm[m - 2], v, join: false });
      else if (this.sharp[k]) { out.push({ s, t, n: nrm[k - 1], v, join: false }); out.push({ s, t, n: nrm[k], v, join: true }); }
      else { const a = nrm[k - 1], b = nrm[k], l = Math.hypot(a[0] + b[0], a[1] + b[1]) || 1; out.push({ s, t, n: [(a[0] + b[0]) / l, (a[1] + b[1]) / l], v, join: true }); }
    }
    return out;
  }
}

// Quads between two rings of entries; winding follows the analytic normals.
function quads(idx, pos, nor, r0, r1, E) {
  const P = (i) => new THREE.Vector3(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
  for (let e = 0; e < E.length - 1; e++) {
    if (!E[e].join) continue;
    const a = r0 + e, b = r1 + e, c = r1 + e + 1, d = r0 + e + 1;
    const pa = P(a), n = P(b).sub(pa).cross(P(d).sub(pa));
    if (n.lengthSq() < 1e-14) { const n2 = P(c).sub(P(b)).cross(P(d).sub(P(b))); n.copy(n2); }
    const an = new THREE.Vector3(nor[3 * a] + nor[3 * d], nor[3 * a + 1] + nor[3 * d + 1], nor[3 * a + 2] + nor[3 * d + 2]);
    if (n.dot(an) >= 0) idx.push(a, b, c, a, c, d); else idx.push(a, c, b, a, d, c);
  }
}
function build(pos, nor, uv, idx) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); return g;
}

// Sweep a profile along a path. `up` is the profile's t axis (fixed for the whole path); s runs
// along cross(tangent, up) * sign, or toward `toward` for a closed path. Open ends are capped.
export function sweep(prof, path, o = {}) {
  const up = (o.up || Y).clone().normalize(), closed = !!o.closed, n = path.length;
  const segN = closed ? n : n - 1;
  const E = prof.entries();
  const tang = [], side = [];
  for (let j = 0; j < segN; j++) { const t = path[(j + 1) % n].clone().sub(path[j]).normalize(); tang.push(t); side.push(new THREE.Vector3().crossVectors(t, up).normalize().multiplyScalar(o.sign ?? 1)); }
  if (o.toward || o.away) { const c = path[0].clone().lerp(path[1], .5), d = side[0].dot((o.toward || o.away).clone().sub(c)); if (o.toward ? d < 0 : d > 0) side.forEach((v) => v.negate()); }
  const smooth = Math.cos(o.smooth ?? .5);
  const isEnd = (i) => !closed && (i === 0 || i === n - 1);
  const sharpAt = (i) => !isEnd(i) && tang[(i - 1 + segN) % segN].dot(tang[i % segN]) < smooth;
  const miter = (i) => {
    const sp = closed || i > 0 ? side[(i - 1 + segN) % segN] : null, sn = closed || i < segN ? side[i % segN] : null;
    if (!sp) return sn.clone(); if (!sn) return sp.clone();
    const m = sp.clone().add(sn); const l = m.length(); if (l < 1e-6) return sn.clone(); m.divideScalar(l);
    return m.divideScalar(Math.max(m.dot(sn), .25));
  };
  const pos = [], nor = [], uv = [], idx = [];
  const ring = (i, nside, arc) => {
    const base = pos.length / 3, p = path[i % n], m = miter(i % n);
    for (const e of E) {
      pos.push(p.x + m.x * e.s + up.x * e.t, p.y + m.y * e.s + up.y * e.t, p.z + m.z * e.s + up.z * e.t);
      const nx = nside.x * e.n[0] + up.x * e.n[1], ny = nside.y * e.n[0] + up.y * e.n[1], nz = nside.z * e.n[0] + up.z * e.n[1], l = Math.hypot(nx, ny, nz) || 1;
      nor.push(nx / l, ny / l, nz / l); uv.push(arc / (o.uScale || 1), e.v / (o.uScale || 1));
    }
    return base;
  };
  const norm = (v) => v.clone().normalize();
  let arc = 0;
  let prev = ring(0, isEnd(0) || sharpAt(0) ? side[0] : norm(miter(0)), 0);
  for (let j = 0; j < segN; j++) {
    const i1 = j + 1; arc += path[(j + 1) % n].distanceTo(path[j]);
    const end = isEnd(i1 % n) || (!closed && i1 === n - 1) ? side[j] : sharpAt(i1 % n) ? side[j] : norm(miter(i1 % n));
    const r1 = ring(i1, end, arc);
    quads(idx, pos, nor, prev, r1, E);
    prev = (j < segN - 1 && sharpAt(i1 % n)) ? ring(i1, side[(j + 1) % segN], arc) : r1;
  }
  const g = build(pos, nor, uv, idx);
  if (!closed && o.caps !== false) {
    const caps = [g];
    for (const [i, dir] of [[0, tang[0].clone().negate()], [n - 1, tang[segN - 1].clone()]]) caps.push(profileCap(prof, path[i], miter(i), up, dir));
    return mergeGeometries(caps.map(clean));
  }
  return g;
}
function profileCap(prof, p, side, up, dir) {
  const pts2 = prof.pts.map(([s, t]) => new THREE.Vector2(s, t));
  const tris = THREE.ShapeUtils.triangulateShape(pts2, []);
  const pos = [], nor = [], idx = [];
  for (const [s, t] of prof.pts) { pos.push(p.x + side.x * s + up.x * t, p.y + side.y * s + up.y * t, p.z + side.z * s + up.z * t); nor.push(dir.x, dir.y, dir.z); }
  for (const [a, b, c] of tris) {
    const A = V(pos[3 * a], pos[3 * a + 1], pos[3 * a + 2]), B = V(pos[3 * b], pos[3 * b + 1], pos[3 * b + 2]), Cc = V(pos[3 * c], pos[3 * c + 1], pos[3 * c + 2]);
    if (B.sub(A).cross(Cc.sub(A)).dot(dir) >= 0) idx.push(a, b, c); else idx.push(a, c, b);
  }
  return build(pos, nor, new Array(prof.pts.length * 2).fill(0), idx);
}

// Turn a profile (s = radius, t = height) about the y axis.
export function lathe(prof, seg = 24, o = {}) {
  const E = prof.entries(), pos = [], nor = [], uv = [], idx = [];
  const a0 = o.a0 || 0, a1 = o.a1 ?? TAU;
  let prev = -1;
  for (let k = 0; k <= seg; k++) {
    const a = a0 + (a1 - a0) * k / seg, c = Math.cos(a), s = Math.sin(a), base = pos.length / 3;
    for (const e of E) { pos.push(e.s * c, e.t, e.s * s); const l = Math.hypot(e.n[0], e.n[1]) || 1; nor.push(e.n[0] * c / l, e.n[1] / l, e.n[0] * s / l); uv.push(k / seg, e.v); }
    if (prev >= 0) quads(idx, pos, nor, prev, base, E);
    prev = base;
  }
  return build(pos, nor, uv, idx);
}

// ---------------------------------------------------------------- the mouldings, by name
// Interior cornice, unit height; scale it to the room. Bed moulding, dentil band, ovolo, corona, cymatium.
export const CORNICE = new Profile(0, 0).fillet(.04, .03).cymaReversa(.07, .09).fillet(.015, .02).up(.13)
  .fillet(.02, .02).ovolo(.12, .1).fillet(.02, .015).out(.3).up(.17).fillet(.025, .02).cymaRecta(.16, .2).up(.03).back();
export const DENTIL_BAND = { t0: .14, t1: .27, s: .155 }; // where the dentils sit in CORNICE units
// Architrave and frieze beneath a cornice, for rooms with an order (unit: the cornice height).
export const ARCHITRAVE_FRIEZE = new Profile(0, 0).fillet(.05, .18).fillet(.025, .22).ovolo(.04, .05).fillet(.015, .03).to(.03, .33).up(.62).to(0, 1.43);
export const BASE = new Profile(0, 0).out(.05).up(.2).fillet(.008, .012).cymaReversa(-.03, .05).up(.012).back();
export const CHAIR_RAIL = new Profile(0, 0).cove(.022, .022).fillet(.008, .006).torus(.022).fillet(-.004, .006).cymaReversa(-.02, .02).back();
export const DOOR_ARCH = new Profile(0, 0).up(.05).out(.012).cymaReversa(.03, .012).out(.07).fillet(.012, .006).out(.04).up(.004).cymaRecta(.05, .02).out(.016).to(.23, 0);
export const PANEL_MOULD = new Profile(0, 0).up(.008).cymaReversa(.025, .018).torus(.008).to(.06, 0);
export const STRING = new Profile(0, 0).fillet(.03, .04).cymaReversa(.04, .05).up(.06).fillet(.02, .02).back();
export const BEAD = new Profile(0, 0).torus(.012, 6).back();

// The North Portico entablature in feet (HABS sheet 76: 6'-1" overall): two-fascia architrave,
// plain frieze, dentil and modillion cornice with a cyma recta crown.
export const ENTAB_FT = new Profile(0, 0).up(.75).fillet(.08, .7).cymaReversa(.12, .18).fillet(.05, .1)
  .to(.06, 1.75).up(1.6).fillet(.05, .06).cymaReversa(.12, .2).up(.38).fillet(.05, .06).ovolo(.25, .22).out(.95).up(.6)
  .fillet(.06, .06).cymaRecta(.38, .42).up(.07).back();
export const ENTAB_DENTILS = { t0: 3.62, t1: 3.98, s0: .23, d: .2 }; // ft
export const ENTAB_MODILLIONS = { t0: 4.27, s0: .53, len: .95 };
export const PLINTH_FT = new Profile(0, 0).out(.45).up(1.1).fillet(-.05, .1).cymaReversa(-.2, .3).up(.05).back();
export const STRING_FT = new Profile(0, 0).fillet(.25, .55).cymaReversa(.12, .2).fillet(-.05, .06).cymaReversa(-.2, .25).back();
export const BALUSTRADE_RAIL_FT = new Profile(0, 0).fillet(.05, .08).cymaReversa(.12, .14).up(.25).fillet(.04, .06).cymaRecta(.08, .1).up(.04).back();
export const BALUSTRADE_BASE_FT = new Profile(0, 0).fillet(.1, .45).cymaReversa(-.12, .15).up(.05).back();

// ---------------------------------------------------------------- turned work
// Attic base, unit diameter.
const ATTIC = new Profile(0, 0).to(.58, 0).up(.08).torus(.045, 5).fillet(-.04, .008).scotia(.035, 4).fillet(.01, .01).torus(.035, 5).fillet(-.02, .01).cove(-.03, .03, 3).back();
const DORIC_CAP = new Profile(0, 0).to(.5, 0).torus(.025).fillet(-.015, .1).fillet(.02, .015).fillet(-.005, .01).ovolo(.12, .12).up(.01).back();
const IONIC_ECHINUS = new Profile(0, 0).to(.5, 0).torus(.03, 4).fillet(-.02, .01).ovolo(.1, .1, 5).up(.03).to(0, .2);
const ROSETTE = new Profile(0, 0).to(.5, 0).ovolo(-.15, .14).cove(-.12, .06).ovolo(-.2, .12).to(0, .34);
const BALUSTER = new Profile(0, 0).to(.17, 0).up(.05).torus(.02, 3).fillet(-.03, .005).cove(-.06, .07, 3).to(.085, .2).curve(.085, .3, (u) => [Math.sin(u * Math.PI) * .9 - u * .25, u], 6)
  .curve(-.03, .18, (u) => [u * u, u], 3).fillet(.03, .015).torus(.02, 3).fillet(.03, .02).up(.075).back();

const shaftCache = new Map();
// A column shaft with entasis: diameter d at the foot, d * taper at the neck. Fluted when flutes > 0.
export function shaft(d, h, { taper = .84, flutes = 0, seg = 28 } = {}) {
  const key = [d, h, taper, flutes, seg].join();
  if (shaftCache.has(key)) return shaftCache.get(key);
  const rings = 14, r = (y) => { const u = y / h; return d / 2 * (u < 1 / 3 ? 1 : 1 - (1 - taper) * Math.sin((u - 1 / 3) * 1.5 * H) ** 1.4); };
  const around = flutes ? flutes * 8 : seg;
  const pos = [], uv = [], idx = [];
  for (let i = 0; i <= rings; i++) {
    const y = h * i / rings, R = r(y), fade = Math.min(1, Math.min(y, h - y) / (h * .05));
    for (let k = 0; k <= around; k++) {
      const a = TAU * k / around; let rr = R;
      if (flutes) { const f = (k % 8) / 8, w = .78; if (f > (1 - w) / 2 && f < 1 - (1 - w) / 2) { const x = (f - .5) / (w / 2); rr -= R * .06 * Math.sqrt(Math.max(0, 1 - x * x)) * fade; } }
      pos.push(Math.cos(a) * rr, y, Math.sin(a) * rr); uv.push(k / around, y / h);
    }
  }
  const W = around + 1;
  for (let i = 0; i < rings; i++) for (let k = 0; k < around; k++) { const a = i * W + k, b = a + 1, c = a + W, e = c + 1; idx.push(a, c, b, b, c, e); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
  shaftCache.set(key, g); return g;
}

// A volute: a scroll on a disc, facing +z, centred on the origin, radius R.
function volute(R, depth) {
  const pts = [];
  const turns = 2.4, N = 36;
  for (let i = 0; i <= N; i++) { const th = i / N * turns * TAU, r = R * .92 * Math.pow(.42, th / TAU); pts.push(new THREE.Vector3(Math.sin(th) * r, -Math.cos(th) * r, depth * .55)); }
  const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 44, R * .08, 4, false);
  const disc = new THREE.CylinderGeometry(R, R, depth, 16, 1).rotateX(H).translate(0, 0, depth * .05);
  const eye = new THREE.SphereGeometry(R * .16, 6, 4).translate(0, 0, depth * .55);
  return [tube, disc, eye];
}

// Capital heights, in units of the neck diameter.
const CAPH = { corinthian: 1.09, ionic: .29, doric: .405 };
// An abacus: a square slab whose edge is an ogee, its core of half-width k, from y0 up.
function abacus(k, y0, proj) {
  const ab = new Profile(0, 0).cymaReversa(proj, proj * .9).up(proj * .7).back();
  const sq = [V(-k, y0, -k), V(k, y0, -k), V(k, y0, k), V(-k, y0, k)];
  return merge([sweep(ab, sq, { closed: true, away: V(0, y0, 0) }), bx(2 * k, ab.height, 2 * k, 0, y0 + ab.height / 2, 0)]);
}
// Ionic capital with four angled volutes (as at the North Portico), unit diameter at the neck.
export function ionicCapital() {
  const g = [lathe(IONIC_ECHINUS, 20)];
  for (let k = 0; k < 4; k++) {
    const a = H / 2 + k * H;
    for (const part of volute(.2, .08)) g.push(part.applyMatrix4(M4(Math.cos(a) * .5, .04, Math.sin(a) * .5, 0, H - a, 0)));
    const b = a + H / 2; // a festoon between each pair of volutes
    g.push(new THREE.TorusGeometry(.15, .026, 4, 10, Math.PI).applyMatrix4(M4(Math.cos(b) * .52, .12, Math.sin(b) * .52, 0, H - b, Math.PI)));
  }
  g.push(abacus(.5, .2, .06));
  return merge(g);
}
// Corinthian capital: bell, two rows of acanthus, corner volutes, abacus. Unit diameter at the neck.
export function corinthianCapital() {
  const g = [];
  const bell = new Profile(0, 0).to(.5, 0).torus(.025).up(.01).curve(.12, .9, (u) => [u * u, u], 8).up(.02).back();
  g.push(lathe(bell, 16));
  const leaf = (w, h, curl) => {
    const p = new THREE.PlaneGeometry(1, 1, 2, 5); const a = p.attributes.position;
    for (let i = 0; i < a.count; i++) {
      const x = a.getX(i), v = a.getY(i) + .5;
      const wid = Math.sin(Math.PI * Math.min(1, v * 1.15)) * (1 + .18 * Math.sin(v * 18)) * w;
      a.setXYZ(i, x * wid, v * h, curl * v * v * v * h + Math.abs(x) * .06 * w - .04 * v * h);
    }
    p.computeVertexNormals(); return p;
  };
  for (let row = 0; row < 2; row++) {
    const n = 8, h = row ? .66 : .4, w = row ? .26 : .3;
    for (let k = 0; k < n; k++) { const a = (k + row * .5) / n * TAU; g.push(leaf(w, h, .5).applyMatrix4(M4(Math.cos(a) * (.53 + row * .02), .06, Math.sin(a) * (.53 + row * .02), 0, H - a, 0))); }
  }
  for (let k = 0; k < 4; k++) { const a = H / 2 + k * H; for (const part of volute(.09, .05)) g.push(part.applyMatrix4(M4(Math.cos(a) * .7, .84, Math.sin(a) * .7, 0, H - a, 0))); }
  g.push(abacus(.58, .98, .05));
  g.push(lathe(ROSETTE, 8).applyMatrix4(M4(0, 1.03, .66, H, 0, 0, .22, .22, .22)));
  return merge(g);
}
export function doricCapital() { return merge([lathe(DORIC_CAP, 20), bx(1.4, .1, 1.4, 0, .355, 0)]); }
export function atticBase(square = true) { const g = [lathe(ATTIC, 20)]; if (square) g.push(bx(1.36, .08, 1.36, 0, .04, 0)); return merge(g); }
export const rosette = (seg = 16) => lathe(ROSETTE, seg);
export const baluster = (seg = 8) => merge([lathe(BALUSTER, seg), bx(.36, .05, .36, 0, .025, 0), bx(.3, .04, .3, 0, .85, 0)]);
const capital = (order) => (order === 'corinthian' ? corinthianCapital() : order === 'ionic' ? ionicCapital() : doricCapital());
const capCache = {};
const capOf = (order) => capCache[order] || (capCache[order] = capital(order));
const baseG = atticBase();

// Whole column: base, shaft, capital, as two parts (shaft; base and capital). d = foot diameter, h = overall height.
export function column(order, d, h, { flutes = 0 } = {}) {
  const neck = d * .84, baseH = .368 * d, capH = CAPH[order] * neck;
  const sh = shaft(d, h - baseH - capH, { flutes }).clone().translate(0, baseH, 0);
  const cap = capOf(order).clone().applyMatrix4(M4(0, h - capH, 0, 0, 0, 0, neck, neck, neck));
  const base = baseG.clone().applyMatrix4(M4(0, 0, 0, 0, 0, 0, d, d, d));
  return { shaft: sh, gilt: merge([cap, base]) };
}

// A flat pilaster on a wall (front faces +z): width w, projection p, height h, fluted face, flattened capital and base.
export function pilaster(order, w, p, h, { flutes = 7 } = {}) {
  const baseH = .368 * w, capH = CAPH[order] * w * .92;
  const sh = new THREE.Shape(); sh.moveTo(-w / 2, 0); sh.lineTo(-w / 2, -p);
  if (flutes) {
    const edge = w * .1, fw = (w - 2 * edge) / flutes, r = fw * .38;
    for (let k = 0; k < flutes; k++) { const c = -w / 2 + edge + fw * (k + .5); sh.lineTo(c - r, -p); sh.absarc(c, -p, r, Math.PI, 0, true); }
  }
  sh.lineTo(w / 2, -p); sh.lineTo(w / 2, 0); sh.lineTo(-w / 2, 0);
  const shaftG = new THREE.ExtrudeGeometry(sh, { depth: h - baseH - capH, bevelEnabled: false, curveSegments: 4 }).rotateX(-H).translate(0, baseH, 0);
  const cap = capOf(order).clone().applyMatrix4(M4(0, h - capH, 0, 0, 0, 0, w * .92, w * .92, p * 1.7));
  const base = baseG.clone().applyMatrix4(M4(0, 0, 0, 0, 0, 0, w, w, p * 1.5));
  return { shaft: shaftG, gilt: merge([cap, base]) };
}

// ---------------------------------------------------------------- framed work in a plane (local x along, y up, z out)
const rectPath = (x0, y0, x1, y1, z = 0) => [V(x0, y0, z), V(x1, y0, z), V(x1, y1, z), V(x0, y1, z)];
// A moulded rectangular frame lying on the wall (panel moulding, door or window architrave).
export function frameRect(prof, w, h) {
  return sweep(prof, rectPath(-w / 2, 0, w / 2, h), { closed: true, up: V(0, 0, 1), toward: V(0, h / 2, 0) });
}
// Architrave around three sides of an opening of width w and height h (bottom open), on the wall plane.
export function architrave(prof, w, h) {
  return sweep(prof, [V(-w / 2, 0, 0), V(-w / 2, h, 0), V(w / 2, h, 0), V(w / 2, 0, 0)], { up: V(0, 0, 1), sign: -1 });
}
// A cornice cap: the profile carried across the front and returned to the wall at both ends.
export function cap(prof, w, d, y = 0) {
  const g = sweep(prof, [V(-w / 2, y, 0), V(-w / 2, y, d), V(w / 2, y, d), V(w / 2, y, 0)], { up: Y, sign: 1 });
  const lid = bx(w - .001, .001, d, 0, y + prof.height - .0005, d / 2);
  return merge([g, lid]);
}
// Raking cornice for a pediment of span w and rise r, with its horizontal cornice and tympanum.
export function pediment(prof, w, rise, { segmental = false, depth = .1 } = {}) {
  const parts = [];
  const pr = prof.swapped();
  if (segmental) {
    const R = (w * w / 4 + rise * rise) / (2 * rise), cy = rise - R, a = Math.asin(w / 2 / R), pts = [];
    for (let i = 0; i <= 24; i++) { const t = -a + 2 * a * i / 24; pts.push(V(R * Math.sin(t), cy + R * Math.cos(t), 0)); }
    parts.push(sweep(pr, pts, { up: V(0, 0, 1), sign: -1 }));
    const sh = new THREE.Shape(); sh.moveTo(-w / 2, 0); for (const p of pts) sh.lineTo(p.x, p.y); sh.lineTo(-w / 2, 0);
    parts.push(new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false, curveSegments: 2 }).translate(0, 0, -depth));
  } else {
    parts.push(sweep(pr, [V(-w / 2, 0, 0), V(0, rise, 0), V(w / 2, 0, 0)], { up: V(0, 0, 1), sign: -1, smooth: .01 }));
    const sh = new THREE.Shape(); sh.moveTo(-w / 2, 0); sh.lineTo(0, rise); sh.lineTo(w / 2, 0); sh.lineTo(-w / 2, 0);
    parts.push(new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false }).translate(0, 0, -depth));
  }
  return merge(parts);
}

// Glazed sash: frame and glazing bars (one geometry) and the glass (another). Local: centred on x, y from 0.
export function sash(w, h, cols, rows, bar = .035, frame = .07, depth = .06) {
  const wood = [bx(w, frame, depth, 0, frame / 2, 0), bx(w, frame, depth, 0, h - frame / 2, 0), bx(frame, h, depth, -w / 2 + frame / 2, h / 2, 0), bx(frame, h, depth, w / 2 - frame / 2, h / 2, 0)];
  const iw = w - 2 * frame, ih = h - 2 * frame;
  for (let c = 1; c < cols; c++) wood.push(bx(bar, ih, depth * .8, -iw / 2 + iw * c / cols, h / 2, 0));
  for (let r = 1; r < rows; r++) wood.push(bx(iw, bar, depth * .8, 0, frame + ih * r / rows, 0));
  wood.push(bx(iw, bar * 1.6, depth * 1.1, 0, h / 2, .005)); // meeting rail
  const glass = new THREE.PlaneGeometry(iw, ih).translate(0, h / 2, -.005);
  return { wood: merge(wood), glass };
}

// A scroll console (bracket) for window surrounds: a shape extruded to thickness t, facing +z. Unit height.
export function console_(t = 1) {
  const s = new THREE.Shape();
  s.moveTo(0, 0); s.bezierCurveTo(.05, .25, .32, .3, .3, .55); s.bezierCurveTo(.28, .8, .42, .92, .45, 1); s.lineTo(0, 1); s.lineTo(0, 0);
  return new THREE.ExtrudeGeometry(s, { depth: t, bevelEnabled: true, bevelSize: .015, bevelThickness: .015, bevelSegments: 2, curveSegments: 8 }).translate(0, 0, -t / 2).rotateY(-H);
}
// A modillion: a scrolled block under the corona, unit length (out from the wall), facing down.
export function modillion() {
  const s = new THREE.Shape();
  s.moveTo(0, 0); s.lineTo(1, 0); s.lineTo(1, -.12); s.bezierCurveTo(.95, -.3, .7, -.28, .62, -.2); s.bezierCurveTo(.45, -.2, .35, -.42, .12, -.45); s.lineTo(0, -.45); s.lineTo(0, 0);
  return new THREE.ExtrudeGeometry(s, { depth: .4, bevelEnabled: false, curveSegments: 6 }).translate(0, 0, -.2).rotateY(-H);
}

// Curtain: a folded panel, width w, drop h, hung from y=h down; folds along x. Faces +z.
export function curtain(w, h, folds = 7, amp = .06) {
  const p = new THREE.PlaneGeometry(w, h, folds * 6, 8).translate(0, h / 2, 0); const a = p.attributes.position;
  for (let i = 0; i < a.count; i++) { const x = a.getX(i), y = a.getY(i), u = (x / w + .5) * folds * TAU, flare = 1 + .5 * (1 - y / h); a.setZ(i, Math.sin(u) * amp * flare); a.setX(i, x * (1 + .08 * (1 - y / h))); }
  p.computeVertexNormals(); return p;
}
// Swagged valance across a window: hanging festoons.
export function swags(w, n = 3, drop = .35) {
  const g = []; const sw = w / n;
  for (let k = 0; k < n; k++) g.push(new THREE.TorusGeometry(sw / 2, drop * .3, 6, 18, Math.PI).applyMatrix4(M4(-w / 2 + sw * (k + .5), 0, 0, Math.PI, 0, 0, 1, drop / (sw / 2), .5)));
  return merge(g);
}

// Coffer: a sunk panel framed by beams. w x d is the panel opening at the beam soffit, dp the depth, bw the beam
// width (each coffer carries half of it). Local y=0 is the ceiling; the beams hang to y=-dp.
export function coffer(w, d, dp, bw = dp, { rose = true } = {}) {
  const pr = new Profile(-bw / 2, 0).to(0, 0).up(dp * .25).cymaReversa(dp * .12, dp * .25).fillet(dp * .05, dp * .12).cymaRecta(dp * .18, dp * .33).up(dp * .05).to(-bw / 2, dp);
  const path = [V(-w / 2, -dp, -d / 2), V(w / 2, -dp, -d / 2), V(w / 2, -dp, d / 2), V(-w / 2, -dp, d / 2)];
  const parts = [sweep(pr, path, { closed: true, up: Y, toward: V(0, -dp, 0) })];
  if (rose) { const k = Math.min(w, d); parts.push(rosette(8).applyMatrix4(M4(0, 0, 0, Math.PI, 0, 0, k * .3, k * .1, k * .3))); }
  return merge(parts);
}

// The round head of an arched window or mirror: a half disc of glass with radiating and ring bars. Local y=0 at the springing.
export function archTop(w, rays = 6, segs = 24, bar = .04) {
  const r = w / 2, wood = [];
  const glass = new THREE.CircleGeometry(r * .97, segs, 0, Math.PI);
  for (let k = 1; k < rays; k++) { const a = Math.PI * k / rays; wood.push(bx(bar, r, bar * 1.6, 0, r / 2, 0).applyMatrix4(M4(0, 0, 0, 0, 0, a - H))); }
  wood.push(new THREE.TorusGeometry(r * .45, bar * .6, 4, segs, Math.PI), new THREE.TorusGeometry(r * .97, bar, 4, segs, Math.PI), bx(w, bar * 1.6, bar * 1.6, 0, 0, 0));
  return { wood: merge(wood), glass };
}
// Architrave up the jambs and round the head of an arched opening of width w, springing at height hs.
export function archArchitrave(prof, w, hs) {
  const pts = [V(-w / 2, 0, 0), V(-w / 2, hs, 0)];
  for (let i = 1; i < 24; i++) { const a = Math.PI - Math.PI * i / 24; pts.push(V(Math.cos(a) * w / 2, hs + Math.sin(a) * w / 2, 0)); }
  pts.push(V(w / 2, hs, 0), V(w / 2, 0, 0));
  return sweep(prof, pts, { up: V(0, 0, 1), sign: -1 });
}

// A marble chimneypiece against a wall (front +z), width w, with a firebox, hearth and an overmantel mirror.
export function mantel(w = 1.9, h = 1.3) {
  const marble = [], gilt = [], black = [], mirror = [];
  const jw = .26, d = .3, fw = w - 2 * jw - .08, fh = h * .72;
  for (const sx of [-1, 1]) {
    marble.push(bx(jw, fh, d, sx * (w / 2 - jw / 2 - .04), fh / 2, d / 2));
    gilt.push(frameRect(PANEL_MOULD.scaled(.7), jw - .08, fh - .2).translate(sx * (w / 2 - jw / 2 - .04), .1, d + .001));
  }
  marble.push(bx(w - .08, h - fh, d, 0, fh + (h - fh) / 2, d / 2));
  gilt.push(rosette(10).applyMatrix4(M4(0, fh + (h - fh) / 2, d, H, 0, 0, .12, .05, .12)));
  marble.push(cap(CORNICE.scaled(.16), w + .12, d + .02, h));
  black.push(bx(fw, fh, .02, 0, fh / 2, .03));
  marble.push(bx(w + .5, .04, .55, 0, .02, .27));
  // overmantel mirror in a gilt frame
  const mw = w * .82, mh = 1.5;
  mirror.push(new THREE.PlaneGeometry(mw, mh).translate(0, h + .3 + mh / 2, .02));
  gilt.push(architrave(DOOR_ARCH.scaled(.6), mw, mh).translate(0, h + .3, .02));
  gilt.push(bx(mw + .3, .06, .05, 0, h + .3, .03));
  gilt.push(lathe(ROSETTE, 10).applyMatrix4(M4(0, h + .3 + mh + .18, .04, H, 0, 0, .3, .1, .3)));
  return { marble: merge(marble), gilt: merge(gilt), black: merge(black), mirror: merge(mirror) };
}
