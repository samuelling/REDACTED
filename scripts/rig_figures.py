"""Rig the CC0 Blender Studio bodies and drive them with CMU motion capture, for the redacted figures.

    blender-python rig_figures.py -- BUNDLE.blend BVH_DIR OUT_DIR

Bodies: GEO-body_{male,female}_realistic from the Blender Studio Human Base Meshes bundle (CC0), plus an
in-between body (the two share one topology) for people whose sex the files do not give.
Motion: the CMU Graphics Lab Motion Capture Database (free for research and commercial use) in Bruce
Hahne's BVH conversion. Clips: 07_04 slow walk, 77_02 standing, 114_05 sitting in a chair.

Method: the BVH skeleton is fitted inside each body (scaled, joints moved to the body's landmarks, arms
lowered into the body's A-pose and applied as rest), the mesh is bound with bone-heat weights, then every
bone copies the world orientation of its mocap twin and the hips copy its (scaled) position. One gait cycle
is cut from the walk and made to run in place; the forward speed goes into figures.json.
Writes OUT_DIR/figure_{m,f,u}.glb and OUT_DIR/figures.json.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

blend, bvh_dir, out = sys.argv[-3], Path(sys.argv[-2]), Path(sys.argv[-1])
out.mkdir(parents=True, exist_ok=True)
FPS_SRC, STEP = 120, 4  # bake every 4th mocap frame: 30 fps
CLIPS = {'walk': '07_04.bvh', 'idle': '77_02.bvh', 'sit': '114_05.bvh'}


def body_mesh(tag):
    bpy.ops.wm.open_mainfile(filepath=blend)
    names = {'m': 'GEO-body_male_realistic', 'f': 'GEO-body_female_realistic'}
    keep = [bpy.data.objects[names['m']], bpy.data.objects[names['f']]]
    for o in list(bpy.data.objects):
        if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
    for o in keep:
        for m in list(o.modifiers): o.modifiers.remove(m)  # the base cage, no multires
        o.data.shape_keys and o.shape_key_clear()
    m, f = keep
    mesh = (m if tag == 'm' else f)
    other = f if mesh is m else m
    if tag == 'u':  # the two bodies share topology: average them
        assert len(m.data.vertices) == len(f.data.vertices)
        mw, fw = m.matrix_world, f.matrix_world
        for vm, vf in zip(m.data.vertices, f.data.vertices):
            vm.co = mw.inverted() @ ((mw @ vm.co + fw @ vf.co) / 2)
        mesh, other = m, f
    bpy.data.objects.remove(other, do_unlink=True)
    bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for p in mesh.data.polygons: p.use_smooth = True
    # stand on z=0, centred
    v = np.array([vv.co[:] for vv in mesh.data.vertices])
    off = Vector((-(v[:, 0].max() + v[:, 0].min()) / 2, -(v[:, 1].max() + v[:, 1].min()) / 2, -v[:, 2].min()))
    for vv in mesh.data.vertices: vv.co += off
    mesh.name = 'body'
    return mesh


def landmarks(mesh):
    v = np.array([vv.co[:] for vv in mesh.data.vertices]); H = v[:, 2].max()
    J = {'H': H}
    for sign, s in ((1, 'L'), (-1, 'R')):
        side = v[v[:, 0] * sign > 0]
        tip = side[np.argmax(np.abs(side[:, 0]))]
        sh = np.array([sign * .165 * H / 1.69, -.01, .805 * H])
        d = tip - sh; L = np.linalg.norm(d); d /= L
        J[s] = dict(sh=sh, d=d, L=L, el=sh + d * L * .45, wr=sh + d * L * .78, tip=sh + d * L * .97,
                    hip=np.array([sign * .095 * H / 1.69, .0, .50 * H]), knee=np.array([sign * .09 * H / 1.69, -.01, .285 * H]),
                    ankle=np.array([sign * .085 * H / 1.69, .03, .045 * H]), ball=np.array([sign * .09 * H / 1.69, -.10 * H / 1.69, .012 * H]),
                    toe=np.array([sign * .09 * H / 1.69, -.16 * H / 1.69, .01 * H]), clav=np.array([sign * .03, .0, .79 * H]))
    J['spine'] = [np.array([0, .0, f * H]) for f in (.53, .60, .67, .76, .83, .87, .91, 1.0)]  # hips..head top
    return J


def import_bvh(name):
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=str(bvh_dir / name), axis_forward='-Z', axis_up='Y', rotate_mode='NATIVE', update_scene_fps=False, update_scene_duration=False)
    arm = (set(bpy.data.objects) - before).pop()
    return arm


def frame_world(arm, frame, bone):
    bpy.context.scene.frame_set(frame)
    return arm.matrix_world @ arm.pose.bones[bone].head


def fit_target(src, J):
    """A copy of the BVH armature, resized to the body and posed into its A-pose, applied as rest."""
    sc = bpy.context.scene; sc.frame_set(1)
    # face the same way as the body (-Y): the left leg must be on +x
    lx = frame_world(src, 1, 'LeftUpLeg').x - frame_world(src, 1, 'Hips').x
    if lx < 0: src.rotation_euler.z += math.pi
    bpy.context.view_layer.update()
    tgt = src.copy(); tgt.data = src.data.copy(); tgt.animation_data_clear(); sc.collection.objects.link(tgt); tgt.name = 'rig'
    bpy.context.view_layer.objects.active = tgt
    for o in bpy.context.selected_objects: o.select_set(False)
    tgt.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = tgt.data.edit_bones
    V3 = lambda a: Vector(a.tolist())
    for b in eb: b.use_connect = False
    # Each bone is moved onto the body's own segment by the smallest rotation of its mocap rest frame, so the frames
    # stay related to the mocap's exactly (bone directions change, twist does not) and orientations copy across.
    def put(name, head, tail):
        b = eb.get(name)
        if b is None: return
        R = b.matrix.to_3x3(); d = (b.tail - b.head).normalized(); want = (V3(tail) - V3(head))
        L = max(want.length, .02); q = d.rotation_difference(want.normalized())
        M = (q.to_matrix() @ R).to_4x4(); M.translation = V3(head)
        b.matrix = M; b.length = L
        return q
    sp = J['spine']
    put('Hips', sp[0], sp[0] + np.array([0, 0, .08])); put('LowerBack', sp[0], sp[1]); put('Spine', sp[1], sp[2]); put('Spine1', sp[2], sp[3])
    put('Neck', sp[3], sp[4]); put('Neck1', sp[4], sp[5]); put('Head', sp[5], sp[7])
    for s, side in (('L', 'Left'), ('R', 'Right')):
        j = J[s]
        put(f'{s}HipJoint', sp[0], j['hip']); put(f'{side}UpLeg', j['hip'], j['knee']); put(f'{side}Leg', j['knee'], j['ankle'])
        put(f'{side}Foot', j['ankle'], j['ball']); put(f'{side}ToeBase', j['ball'], j['toe'])
        put(f'{side}Shoulder', j['clav'], j['sh'])
        put(f'{side}Arm', j['sh'], j['el']); qf = put(f'{side}ForeArm', j['el'], j['wr'])
        # the hand keeps its mocap frame relative to the forearm: rotate it with the forearm's correction
        fa = eb.get(f'{side}ForeArm'); h = eb.get(f'{side}Hand')
        for nm, at in ((f'{side}Hand', j['wr']), (f'{side}FingerBase', j['wr'] + j['d'] * j['L'] * .06), (f'{side}HandIndex1', j['wr'] + j['d'] * j['L'] * .1), ('LThumb' if s == 'L' else 'RThumb', j['wr'] + j['d'] * j['L'] * .06)):
            b = eb.get(nm)
            if b and qf is not None: L = b.length; M = (qf.to_matrix() @ b.matrix.to_3x3()).to_4x4(); M.translation = V3(at); b.matrix = M; b.length = max(L, .03)
    bpy.ops.object.mode_set(mode='OBJECT')
    return tgt


def scale_source(src, tgt):
    """Scale the mocap armature so its legs match the body's, for the hips' path."""
    sc = bpy.context.scene; sc.frame_set(1)
    leg = lambda arm, w: (arm.matrix_world @ arm.pose.bones['LeftUpLeg'].head - arm.matrix_world @ arm.pose.bones['LeftFoot'].head).length if w else (arm.data.bones['LeftUpLeg'].head_local - arm.data.bones['LeftFoot'].head_local).length
    k = leg(tgt, False) / leg(src, True)
    src.scale = (k, k, k); bpy.context.view_layer.update()
    # put the mocap's frame-1 hips over the rig's
    d = (tgt.matrix_world @ tgt.data.bones['Hips'].head_local) - (src.matrix_world @ src.pose.bones['Hips'].head)
    src.location += Vector((d.x, d.y, 0)); bpy.context.view_layer.update()
    return k


def bake(src, tgt, name, f0, f1):
    for pb in tgt.pose.bones:
        if pb.name not in src.pose.bones: continue
        c = pb.constraints.new('COPY_ROTATION'); c.target = src; c.subtarget = pb.name; c.target_space = 'WORLD'; c.owner_space = 'WORLD'
        if pb.name == 'Hips':
            c2 = pb.constraints.new('COPY_LOCATION'); c2.target = src; c2.subtarget = 'Hips'; c2.target_space = 'WORLD'; c2.owner_space = 'WORLD'
    bpy.context.view_layer.objects.active = tgt
    for o in bpy.context.selected_objects: o.select_set(False)
    tgt.select_set(True)
    bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, step=STEP, only_selected=True, visual_keying=True, clear_constraints=True, use_current_action=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act = tgt.animation_data.action; act.name = name; act.use_fake_user = True
    return act


def series(arm, bone, f0, f1, step=1):
    out_ = []
    for f in range(f0, f1 + 1, step):
        bpy.context.scene.frame_set(f); out_.append(list(arm.matrix_world @ arm.pose.bones[bone].head))
    return np.array(out_)


def gait_window(src):
    """One full stride from the middle of the walk: two successive minima of the left foot's height."""
    n = int(src.animation_data.action.frame_range[1])
    z = series(src, 'LeftFoot', 2, n)[:, 2]
    zs = np.convolve(z, np.ones(9) / 9, mode='same')
    mins = [i + 2 for i in range(20, len(zs) - 20) if zs[i] == zs[max(0, i - 30):i + 31].min()]
    mid = len(mins) // 2 - 1
    a, b = mins[max(0, mid)], mins[max(0, mid) + 1]
    return a, b


def still_window(src, length, lowest=False):
    """The steadiest stretch of `length` frames (lowest hips, if sitting)."""
    n = int(src.animation_data.action.frame_range[1])
    h = series(src, 'Hips', 2, n, 4)
    best, at = 1e9, 2
    w = length // 4
    for i in range(0, len(h) - w):
        seg = h[i:i + w]
        score = np.ptp(seg[:, 0]) + np.ptp(seg[:, 1]) + (seg[:, 2].mean() * 4 if lowest else 0)
        if score < best: best, at = score, 2 + i * 4
    return at, at + length


def in_place(act, tgt, forward):
    """Take the steady forward travel out of the hips so the cycle runs on the spot."""
    fc = {i: act.fcurves.find('pose.bones["Hips"].location', index=i) for i in range(3)}
    if not fc[0]: return 0
    # hips location keys are in the bone's rest space; take the trend out in world terms by fitting each channel
    speeds = []
    for i in range(3):
        kp = fc[i].keyframe_points; t = np.array([k.co[0] for k in kp]); y = np.array([k.co[1] for k in kp])
        if len(t) < 2: speeds.append(0); continue
        slope = (y[-1] - y[0]) / (t[-1] - t[0]); speeds.append(slope)
    # the axis with the most travel is the walking direction in rest space
    ax = int(np.argmax(np.abs(speeds[:3])))
    for i in range(3):
        kp = fc[i].keyframe_points; t0 = kp[0].co[0]; y0 = kp[0].co[1]
        sl = speeds[i] if i == ax or abs(speeds[i]) > .2 * abs(speeds[ax]) else 0
        for k in kp: k.co[1] -= y0 + sl * (k.co[0] - t0); k.handle_left[1] = k.co[1]; k.handle_right[1] = k.co[1]
    return abs(speeds[ax]) * FPS_SRC  # rig units per second


def centre(act):
    for i in range(2 if False else 3):
        f = act.fcurves.find('pose.bones["Hips"].location', index=i)
        if not f: continue
        ys = [k.co[1] for k in f.keyframe_points]; mean = sum(ys) / len(ys)
        if i == 1: continue  # leave the rest-space axis that carries height (checked below)
        for k in f.keyframe_points: k.co[1] -= mean


def bind(mesh, rig, J):
    """Skin weights: each vertex starts on its nearest bone (arms and legs kept to their own side and region),
    then the weights are diffused over the surface so every joint bends smoothly. (Bone heat fails headless.)"""
    v = np.array([vv.co[:] for vv in mesh.data.vertices]); n = len(v)
    e = np.array([ed.vertices[:] for ed in mesh.data.edges])
    sp = J['spine']
    bones = {'Hips': (sp[0], sp[0] + np.array([0, 0, .06])), 'LowerBack': (sp[0], sp[1]), 'Spine': (sp[1], sp[2]), 'Spine1': (sp[2], sp[3]),
             'Neck': (sp[3], sp[4]), 'Neck1': (sp[4], sp[5]), 'Head': (sp[5], sp[7])}
    for s, side in (('L', 'Left'), ('R', 'Right')):
        j = J[s]
        bones.update({f'{side}Shoulder': (j['clav'], j['sh']), f'{side}Arm': (j['sh'], j['el']), f'{side}ForeArm': (j['el'], j['wr']), f'{side}Hand': (j['wr'], j['tip']),
                      f'{side}UpLeg': (j['hip'], j['knee']), f'{side}Leg': (j['knee'], j['ankle']), f'{side}Foot': (j['ankle'], j['ball']), f'{side}ToeBase': (j['ball'], j['toe'])})
    centre = ['Hips', 'LowerBack', 'Spine', 'Spine1', 'Neck', 'Neck1', 'Head']
    def dist(name):
        a, b = bones[name]; ab = b - a; t = np.clip(((v - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
        return np.linalg.norm(v - (a + t[:, None] * ab), axis=1)
    # the arms: the part of each side beyond the shoulder, connected to the fingertips
    arm = {}
    for s, sign in (('L', 1), ('R', -1)):
        j = J[s]; rel = v - j['sh']; sa = rel @ j['d']
        nrm = np.array([-j['d'][2] * sign, 0, j['d'][0] * sign]); nrm = nrm if nrm[0] * sign > 0 else -nrm
        keep = (sa > .0) & (v[:, 0] * sign > 0) & ((rel @ nrm) > -.075)
        ee = e[keep[e[:, 0]] & keep[e[:, 1]]]
        lab = np.arange(n)
        for _ in range(400):  # label propagation for connected components
            m = np.minimum(lab[ee[:, 0]], lab[ee[:, 1]]); changed = False
            l0 = lab.copy(); np.minimum.at(lab, ee[:, 0], m); np.minimum.at(lab, ee[:, 1], m)
            if (lab == l0).all(): break
        tip = np.argmax(v[:, 0] * sign)
        arm[s] = keep & (lab == lab[tip])
    side = {'L': ['LeftArm', 'LeftForeArm', 'LeftHand'], 'R': ['RightArm', 'RightForeArm', 'RightHand']}
    legs = {'L': ['LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase'], 'R': ['RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase']}
    names = centre + ['LeftShoulder', 'RightShoulder'] + side['L'] + side['R'] + legs['L'] + legs['R']
    D = np.stack([dist(nm) for nm in names], 1)
    allow = np.ones_like(D, bool)
    idx = {nm: i for i, nm in enumerate(names)}
    hipz = J['spine'][0][2]
    for s, sign in (('L', 1), ('R', -1)):
        for nm in side[s]: allow[:, idx[nm]] = arm[s]
        for nm in legs[s]: allow[:, idx[nm]] = (v[:, 0] * sign > -.004) & (v[:, 2] < hipz + .06) & ~arm['L'] & ~arm['R']
    inarm = arm['L'] | arm['R']
    for nm in centre + ['LeftShoulder', 'RightShoulder']: allow[inarm, idx[nm]] = False
    D[~allow] = 1e9
    W = np.zeros_like(D); W[np.arange(n), D.argmin(1)] = 1
    # diffuse across the surface (never across the limb boundaries' forbidden bones)
    deg = np.zeros(n); np.add.at(deg, e[:, 0], 1); np.add.at(deg, e[:, 1], 1)
    for _ in range(18):
        acc = np.zeros_like(W); np.add.at(acc, e[:, 0], W[e[:, 1]]); np.add.at(acc, e[:, 1], W[e[:, 0]])
        W = .5 * W + .5 * acc / np.maximum(deg, 1)[:, None]
        W[~allow] = 0; W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    # four strongest influences
    order = np.argsort(-W, 1); top = np.zeros_like(W, bool); np.put_along_axis(top, order[:, :4], True, 1)
    W[~top] = 0; W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    mesh.parent = rig
    mod = mesh.modifiers.new('rig', 'ARMATURE'); mod.object = rig
    for k, nm in enumerate(names):
        g = mesh.vertex_groups.new(name=nm)
        for i in np.nonzero(W[:, k] > 1e-3)[0]: g.add([int(i)], float(W[i, k]), 'REPLACE')


meta = {}
for tag in (sys.argv[-4].split(',') if len(sys.argv) > 4 and sys.argv[-4] in ('m','f','u','m,f,u') else ('m', 'f', 'u')):
    mesh = body_mesh(tag)
    J = landmarks(mesh)
    first = import_bvh(CLIPS['walk'])
    tgt = fit_target(first, J)
    # bind (nearest bone, limbs kept apart, then diffused across the joints), then thin the mesh
    for o in bpy.context.selected_objects: o.select_set(False)
    mesh.select_set(True); tgt.select_set(True); bpy.context.view_layer.objects.active = tgt
    bind(mesh, tgt, J)
    dec = mesh.modifiers.new('dec', 'DECIMATE'); dec.ratio = .27
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.modifier_move_to_index(modifier='dec', index=0); bpy.ops.object.modifier_apply(modifier='dec')
    info = {'tris': sum(len(p.vertices) - 2 for p in mesh.data.polygons), 'height': J['H']}
    bpy.data.objects.remove(first, do_unlink=True)
    for clip, file in CLIPS.items():
        src = import_bvh(file)
        if clip == 'walk': f0, f1 = gait_window(src)
        elif clip == 'idle': f0, f1 = still_window(src, 6 * FPS_SRC)
        else: f0, f1 = still_window(src, 5 * FPS_SRC, lowest=True)
        # turn the take so the person walks (or faces) toward -Y, the body's front
        if clip == 'walk': fwd = frame_world(src, f1, 'Hips') - frame_world(src, f0, 'Hips')
        else: mid = (f0 + f1) // 2; fwd = (frame_world(src, mid, 'LeftUpLeg') - frame_world(src, mid, 'RightUpLeg')).cross(Vector((0, 0, 1)))
        src.rotation_euler.z += -math.pi / 2 - math.atan2(fwd.y, fwd.x)
        bpy.context.view_layer.update()
        scale_source(src, tgt)
        act = bake(src, tgt, clip, f0, f1)
        if clip == 'walk': info['walk_speed'] = in_place(act, tgt, None); info['walk_seconds'] = (f1 - f0) / FPS_SRC
        else:
            for i in (0, 2):
                f = act.fcurves.find('pose.bones["Hips"].location', index=i)
                if f:
                    ys = [k.co[1] for k in f.keyframe_points]; mean = sum(ys) / len(ys)
                    for k in f.keyframe_points: k.co[1] -= mean; k.handle_left[1] -= mean; k.handle_right[1] -= mean
        info[clip + '_frames'] = [f0, f1]
        tgt.animation_data.action = None
        tr = tgt.animation_data.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 0, act)
        bpy.data.objects.remove(src, do_unlink=True)
    for o in bpy.context.selected_objects: o.select_set(False)
    mesh.select_set(True); tgt.select_set(True)
    bpy.context.scene.render.fps = FPS_SRC; bpy.context.scene.render.fps_base = 1
    print('MODS', [(m.type, getattr(m, 'object', None) and m.object.name) for m in mesh.modifiers], mesh.parent and mesh.parent.name, len(mesh.vertex_groups))
    bpy.ops.export_scene.gltf(filepath=str(out / f'figure_{tag}.glb'), use_selection=True, export_format='GLB', export_materials='NONE', export_yup=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_skins=True, export_morph=False, export_force_sampling=True, export_frame_step=STEP, export_texcoords=False)
    meta[tag] = info
    print('DONE', tag, json.dumps(info), flush=True)
(out / 'figures.json').write_text(json.dumps(meta, indent=1))
