"""Pose the CC0 Blender Studio realistic bodies by bending them at their joints, for the redacted figures.

    python scripts/pose_figures.py RAW_DIR        # RAW_DIR has body_m.glb and body_f.glb (A-pose, Y up, facing +Z)

Writes site/figures/figure_{m,f}_{stand,clasp,fold,sit}.glb, decimated to ~7,000 triangles each.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "figures"


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def rot(axis, ang):
    a = np.asarray(axis, float); a /= np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def bend(v, pivot, axis, ang, w):
    """Rotate each vertex about pivot/axis by ang * w (per-vertex weight), so joints bend smoothly."""
    out = v.copy()
    for k in np.unique(np.round(w, 3)):
        if k <= 0:
            continue
        m = np.isclose(np.round(w, 3), k)
        out[m] = (v[m] - pivot) @ rot(axis, ang * k).T + pivot
    return out


def landmarks(v, H):
    def arm_tip(sign):
        side = v[v[:, 0] * sign > 0]
        return side[np.argmax(np.abs(side[:, 0]))]
    J = {}
    for sign, s in ((1, "L"), (-1, "R")):
        tip = arm_tip(sign)
        sh = np.array([sign * 0.165 * H / 1.69, 0.805 * H, -0.01])
        d = tip - sh; L = np.linalg.norm(d); d /= L
        J[s] = dict(sh=sh, d=d, L=L, el=sh + d * L * 0.47, wr=sh + d * L * 0.80, hip=np.array([sign * 0.09 * H / 1.69, 0.50 * H, 0.0]), knee=np.array([sign * 0.085 * H / 1.69, 0.285 * H, 0.01]))
    return J


def component_beyond(v, edges, j, sign, s_cut, seed):
    """Vertices connected to `seed` once the mesh is cut at arc s_cut along the arm axis."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    rel = v - j["sh"]
    s = rel @ j["d"]
    # Outward normal to the arm in the frontal plane: torso vertices sit well behind it.
    n = np.array([-j["d"][1] * sign, j["d"][0] * sign, 0.0]) * sign
    n = n if n[0] * sign > 0 else -n
    lateral = rel @ n
    keep = (s > s_cut) & (v[:, 0] * sign > 0.0) & (lateral > -0.075)
    e = edges[keep[edges[:, 0]] & keep[edges[:, 1]]]
    n = len(v)
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    _, lab = connected_components(g, directed=False)
    return keep & (lab == lab[seed]), s


def arm_weight(v, edges, j, sign, s0, s1, seed):
    """1 on the arm beyond s1, blending to 0 at s0 across the joint, 0 on the torso."""
    part, s = component_beyond(v, edges, j, sign, s0, seed)
    return smooth(s0, s1, s) * part


def pose(v, H, name, edges):
    J = landmarks(v, H)
    v = v.copy()
    for sign, s in ((1, "L"), (-1, "R")):
        j = J[s]
        # Weights are computed on the rest pose, then applied joint by joint from the hand inwards.
        tip = int(np.argmax(v[:, 0] * sign))
        w_arm = arm_weight(v, edges, j, sign, 0.02, 0.10, tip)
        w_fore = arm_weight(v, edges, j, sign, j["L"] * 0.43, j["L"] * 0.51, tip)
        down = -sign * np.radians(21)                    # bring the arm to the side
        if name in ("clasp", "fold", "sit"):
            fwd = {"clasp": -1.25, "fold": -1.62, "sit": -1.3}[name]
            inward = {"clasp": -sign * 0.55, "fold": -sign * 1.25, "sit": -sign * 0.1}[name]
            v = bend(v, j["el"], [1, 0, 0], fwd, w_fore)
            v = bend(v, j["el"], [0, 1, 0], inward, w_fore)
        v = bend(v, j["sh"], [0, 0, 1], down, w_arm)
        if name == "fold":
            v = bend(v, j["sh"], [1, 0, 0], -0.35, w_arm)
    if name == "sit":
        for sign, s in ((1, "L"), (-1, "R")):
            j = J[s]
            leg = (v[:, 0] * sign > -0.01)
            w_shin = smooth(j["knee"][1] + 0.04, j["knee"][1] - 0.04, v[:, 1]) * leg
            w_leg = smooth(j["hip"][1] + 0.05, j["hip"][1] - 0.07, v[:, 1]) * leg
            v = bend(v, j["knee"], [1, 0, 0], np.radians(88), w_shin)
            v = bend(v, j["hip"], [1, 0, 0], np.radians(-86), w_leg)
    v[:, 1] -= v[:, 1].min()
    return v


def main(raw):
    OUT.mkdir(parents=True, exist_ok=True)
    for tag in "mf":
        m = trimesh.load(Path(raw) / f"body_{tag}.glb", force="mesh")
        m.merge_vertices()
        v = m.vertices.copy(); v[:, 0] -= v[:, 0].mean(); v[:, 2] -= v[:, 2].mean(); v[:, 1] -= v[:, 1].min()
        H = v[:, 1].max()
        for name in ("stand", "clasp", "fold", "sit"):
            pm = trimesh.Trimesh(pose(v, H, name, m.edges_unique), m.faces, process=False)
            pm = pm.simplify_quadric_decimation(face_count=7000)
            # A seated figure's base is the seat: put the hip line at the origin height of a chair seat.
            if name == "sit":
                pm.vertices[:, 1] -= pm.vertices[:, 1].min()
            pm.export(OUT / f"figure_{tag}_{name}.glb")
            print(tag, name, len(pm.faces), pm.bounds.round(2).tolist())


if __name__ == "__main__":
    main(sys.argv[1])
