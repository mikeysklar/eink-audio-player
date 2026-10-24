"""Blender scenes for the eink-audio-player: printed stand plus all the boards.

    blender -b --factory-startup --python render.py -- turntable   # turntable.blend
    blender -b --factory-startup --python render.py -- explode     # explode.blend
    blender -b --factory-startup --python render.py -- check       # EEVEE check stills
    blender -b --factory-startup --python render.py -- hero        # Cycles hero.png, exploded.png
    ./render.sh turntable.blend turntable.mp4                      # Cycles frames + MP4

Everything is placed in the stand's world frame (arcade/layout.py): mm, desk Z=0, Z up,
player at -Y, X the player's right. The printed parts come from arcade/build/*.stl,
already in world coordinates. The boards come from cad/*.glb (export.sh, kicad-cli with
the same user origin as case/build/board.step) and are placed with the two rigid body
matrices in arcade/layout.json: "stack" (board, Feather, TLV, EYESPI, battery, e-ink)
and "keys" (the NeoKey 1x4 with its four MX switches and keycaps).

The glTF importer turns the GLB's Y-up metres into Blender Z-up metres, so an imported
point / 1 mm is the board point p, and world = p0 + p.x*bx + p.y*by + p.z*bz.
"""

import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
CAD = HERE / "cad"
ARC = Path("/Volumes/clear/Downloads/ada/hstx-audio/landing-pad/arcade")
MEDIA = HERE.parent / "docs" / "media" / "blender"
CHECK = Path("/private/tmp/claude-501/bl/check")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = ARGS[0] if ARGS else "check"
MM = 0.001
FPS = 30

LAYOUT = json.loads((ARC / "layout.json").read_text())
N_PLAYER = Vector(LAYOUT["stack"]["normal_to_player"])  # out of the e-ink, toward the player
UP_KEYS = Vector(LAYOUT["keys"]["normal_up"])  # out of the NeoKey face
EZ_ANO = Vector((0, math.sin(math.radians(LAYOUT["deck_deg"])),
                 -math.cos(math.radians(LAYOUT["deck_deg"]))))  # into the ANO mount
HARDWARE = json.loads((ARC / "build" / "fasteners.json").read_text())

# Printed parts and their colours (arcade/assemble_arcade.py COLORS)
RED, BLACK = (0.85, 0.20, 0.30), (0.10, 0.10, 0.12)
PRINTED = {"chassis": RED, "bezel": BLACK, "deck": BLACK, "cradle": BLACK, "handle": RED}
# Pivots that ride on another while it moves (each pivot only ever translates)
PARENT = {"cradle": "bezel", "stack": "bezel", "keys": "deck", "keycaps": "deck"}

# Board parts (export.sh references) -> explode group; all ride on "stack" except the NeoKey
STACK_GROUPS = {
    "board": ["board", "SW1", "R1", "R2", "R3", "R4"],
    "sockets": ["J1", "J2", "J4", "J5", "J9", "J10"],
    "breakouts": ["A1", "A3", "A7"],
    "battery": ["BT1"],
    "display": ["DS1"],
}
# Feather and TLV STEPs have no male headers: black spacers fill socket top to breakout
HEADERS = ["J1", "J2", "J9", "J10"]
SOCKET_TOP, BREAKOUT_BOTTOM = 9.0, 11.49

# Explode: the real assembly run backwards, then forwards. The screws back out, the handle
# pulls out to the left, the ANO lifts off, the deck comes out (the NeoKey drops off its
# pins, the MX switches stay in the plate), the bezel comes out with the stack, and the
# stack comes apart behind it. Coming back is the mirror image. The offsets are spread
# wider than the real paths so every part shows; assemble_arcade.py checks the real ones.
# group -> (offset mm from its parent, (out start, out end) s); back = mirrored about MIRROR
EXPLODE_SECONDS = 8.0
MIRROR = 4.0
MOVES = {
    "handle": (Vector((-80, 0, 0)), (0.7, 1.5)),
    "ano": (-EZ_ANO * 28 + Vector((14, 0, 0)), (0.9, 1.7)),
    "deck": (Vector((0, -78, 12)), (1.1, 2.0)),  # up off its slots, then out the front
    "keys": (-UP_KEYS * 14, (1.9, 2.6)),
    "bezel": (N_PLAYER * 50 + Vector((0, 0, 62)), (1.6, 2.5)),
    "cradle": (N_PLAYER * -14, (2.4, 3.2)),
    "board": (N_PLAYER * -30, (2.4, 3.2)),
    "sockets": (N_PLAYER * -38, (2.4, 3.2)),
    "breakouts": (N_PLAYER * -58, (2.4, 3.2)),
    "battery": (N_PLAYER * -22, (2.5, 3.2)),
}
SCREWS_OUT = (0.3, 0.8)  # every screw backs out along its axis, then rides its part
EXPLODED_AT = 4.0  # s, fully apart

TURN_SECONDS = 10.0
TURN_START_DEG = -35  # azimuth 0 looks from the player (-Y); negative = from the left
ELEVATION_DEG = 22

FR4 = (0.80, 0.72, 0.46)  # milled bare FR4, sRGB
COPPER = (0.96, 0.62, 0.48)
EINK = (0.84, 0.84, 0.80)


def srgb(color):
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in color)


def material(name, color, roughness=0.5, metallic=0.0, coat=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*srgb(color), 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Coat Weight"].default_value = coat
    return mat


def pla(name, color):
    """Matte PLA: rough, a touch of sheen, faint layer-line bump along world Z."""
    mat = material(name, color, roughness=0.62)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Sheen Weight"].default_value = 0.15
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    wave = nodes.new("ShaderNodeMath")
    wave.operation = "SINE"
    scale = nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = 2 * math.pi / (0.2 * MM)  # 0.2 mm layers
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.02 * MM
    links.new(coord.outputs["Object"], sep.inputs[0])
    links.new(sep.outputs["Z"], scale.inputs[0])
    links.new(scale.outputs[0], wave.inputs[0])
    links.new(wave.outputs[0], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def body_matrix(name):
    b = LAYOUT[name]
    m = Matrix.Identity(4)
    for col, key in enumerate(("bx", "by", "bz")):
        for row in range(3):
            m[row][col] = b[key][row]
    for row in range(3):
        m[row][3] = b["p0"][row] * MM
    return m


def bounds(objects):
    points = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
    low = Vector(min(p[i] for p in points) for i in range(3))
    high = Vector(max(p[i] for p in points) for i in range(3))
    return low, high


def smooth(meshes):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
    if meshes:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    bpy.ops.object.select_all(action="DESELECT")


def import_glb(ref, parent):
    """Import cad/<ref>.glb under parent (the board frame); returns its mesh objects."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(CAD / f"{ref}.glb"))
    new = [obj for obj in bpy.data.objects if obj not in before]
    for obj in new:
        if obj.parent is None:
            obj.parent = parent
    meshes = [obj for obj in new if obj.type == "MESH"]
    smooth(meshes)
    return meshes


def fix_materials(meshes, done):
    """kicad-cli marks every GLB material metallic. Keep metal only for pins, terminals
    and shields (gold, tin white, mid neutral grey); the rest is plastic, epoxy or mask."""
    for obj in meshes:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or mat in done:
                continue
            done.add(mat)
            bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if not bsdf:
                continue
            r, g, b, _ = bsdf.inputs["Base Color"].default_value
            gold = r > 0.6 and g > 0.35 and b < 0.12
            tin = min(r, g, b) > 0.97
            grey = max(r, g, b) - min(r, g, b) < 0.03 and 0.28 < r < 0.7
            metal = gold or tin or grey
            bsdf.inputs["Metallic"].default_value = 1.0 if metal else 0.0
            bsdf.inputs["Roughness"].default_value = 0.3 if metal else 0.45


def recolor(meshes, linear_rgb, mat):
    """Swap every material slot whose base colour is linear_rgb (None: all) for mat."""
    for obj in meshes:
        for slot in obj.material_slots:
            col = slot.material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            if linear_rgb is None or all(abs(col[i] - linear_rgb[i]) < 0.02 for i in range(3)):
                slot.material = mat


def header_strip(socket_meshes, frame, mats):
    """Black male-header spacer from the socket top to the breakout, in the board frame."""
    inv = frame.matrix_world.inverted()
    points = [inv @ obj.matrix_world @ Vector(c) for obj in socket_meshes for c in obj.bound_box]
    lo = Vector(min(p[i] for p in points) for i in range(3)) / MM
    hi = Vector(max(p[i] for p in points) for i in range(3)) / MM
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.scale = ((hi.x - lo.x - 0.2) * MM, 2.5 * MM, (BREAKOUT_BOTTOM - SOCKET_TOP) * MM)
    obj.location = ((lo.x + hi.x) / 2 * MM, (lo.y + hi.y) / 2 * MM, (SOCKET_TOP + BREAKOUT_BOTTOM) / 2 * MM)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mats["header"])
    obj.parent = frame
    return obj


def build(mats):
    """Returns {group: pivot empty}; each pivot only ever translates in world."""
    pivots = {}

    for name, color in PRINTED.items():
        pivot = pivots[name] = empty(f"Explode {name}", pivots.get(PARENT.get(name)))
        bpy.ops.wm.stl_import(filepath=str(ARC / "build" / f"{name}.stl"), global_scale=MM)
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(mats["red" if color == RED else "black"])
        smooth([obj])
        obj.parent = pivot

    stack = pivots["stack"] = empty("Explode stack", pivots[PARENT["stack"]])
    done = set()
    glb = {}
    for group, refs in STACK_GROUPS.items():
        pivot = pivots[group] = empty(f"Explode {group}", stack)
        frame = empty(f"Board frame {group}", pivot)
        frame.matrix_world = body_matrix("stack")
        for ref in refs:
            glb[ref] = import_glb(ref, frame)
            if ref != "board":
                fix_materials(glb[ref], done)
    bpy.context.view_layer.update()
    breakout_frame = pivots["breakouts"].children[0]
    for ref in HEADERS:
        header_strip(glb[ref], breakout_frame, mats)

    keys = pivots["keys"] = empty("Explode keys", pivots[PARENT["keys"]])
    frame = empty("Board frame keys", keys)
    frame.matrix_world = body_matrix("keys")
    glb["A5"] = import_glb("A5", frame)
    fix_materials(glb["A5"], done)
    ano = pivots["ano"] = empty("Explode ano")  # on the chassis's ANO mount
    ano_frame = empty("Board frame ano", ano)
    ano_frame.matrix_world = body_matrix("keys")
    glb["ANO1"] = import_glb("ANO1", ano_frame)
    fix_materials(glb["ANO1"], done)
    bpy.context.view_layer.update()
    # The four MX switch + keycap blocks (Cherry MX keycap.wrl) lift further off the NeoKey:
    # the only A5 meshes reaching more than 3 mm out past its face (board z -12.03).
    caps = pivots["keycaps"] = empty("Explode keycaps", pivots[PARENT["keycaps"]])
    inv = frame.matrix_world.inverted()
    blocks = [obj for obj in glb["A5"]
              if min((inv @ obj.matrix_world @ Vector(c)).z for c in obj.bound_box) < -15.0 * MM]
    for obj in blocks:
        world = obj.matrix_world.copy()
        obj.parent = caps
        obj.matrix_world = world
    print(f"[eink] {len(blocks)} key blocks")

    board_frame = pivots["board"].children[0]
    inv = board_frame.matrix_world.inverted()
    for obj in glb["board"]:  # milled FR4 body, bare copper on top (F.Cu at board Z=1.6)
        z0 = min((inv @ obj.matrix_world @ Vector(c)).z for c in obj.bound_box)
        obj.data.materials.clear()
        obj.data.materials.append(mats["copper"] if z0 > 1.0 * MM else mats["fr4"])
    recolor(glb["DS1"], (0.56, 0.66, 0.56), mats["eink"])  # KiCad's grey-green -> paper
    recolor(glb["A5"], (0.79, 0.79, 0.75), mats["keycap"])
    recolor(glb["BT1"], None, mats["pouch"])
    add_hardware(pivots, mats)
    return pivots


def add_hardware(pivots, mats):
    """fasteners.json: each screw on its own pivot (it backs out along its axis), riding the
    part its head bears on; each insert rides the part it is pressed into."""
    meshes = {}
    rides = {"chassis": pivots["chassis"], "bezel": pivots["bezel"], "deck": pivots["deck"],
             "board": pivots["board"], "keys": pivots["keys"], "ano": pivots["ano"]}
    for i, item in enumerate(HARDWARE):
        kind = item["kind"]
        if kind not in meshes:
            bpy.ops.wm.stl_import(filepath=str(ARC / "build" / f"hw_{kind}.stl"), global_scale=MM)
            proto = bpy.context.object
            bpy.ops.object.transform_apply(scale=True)  # the importer scales the object
            proto.data.materials.append(mats["brass" if kind == "insert" else "steel"])
            smooth([proto])
            meshes[kind] = proto.data
            bpy.data.objects.remove(proto, do_unlink=True)
        axis = Vector(item["axis"])
        pivot = empty(f"Hardware {i} {kind}", rides[item["rides"]])
        obj = bpy.data.objects.new(f"{kind} {i}", meshes[kind])
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = pivot
        obj.matrix_world = Matrix.Translation(Vector(item["p"]) * MM) @ \
            Vector((0, 0, -1)).rotation_difference(axis).to_matrix().to_4x4()
        if kind != "insert":
            pivots[f"screw {i}"] = pivot
            MOVES[f"screw {i}"] = (-axis * (item["length"] + 3), SCREWS_OUT)


def key_explode(pivots):
    for name, (offset, out) in MOVES.items():
        back = (2 * MIRROR - out[1], 2 * MIRROR - out[0])
        obj = pivots[name]
        for seconds, f in ((0, 0), (out[0], 0), (out[1], 1), (back[0], 1), (back[1], 0),
                           (EXPLODE_SECONDS, 0)):
            obj.location = offset * MM * f
            obj.keyframe_insert("location", frame=1 + round(seconds * FPS))


def add_floor(mats):
    bpy.ops.mesh.primitive_plane_add(size=8)
    floor = bpy.context.object
    floor.name = "Desk"
    floor.data.materials.append(mats["floor"])


def add_lights(parent, size):
    """Softboxes on the camera rig, so every side is lit the same as it comes round."""
    lights = (("Key", (-1.0, -1.3, 1.4), 9.0, 1.6), ("Fill", (1.4, -0.9, 0.5), 3.0, 2.2),
              ("Rim", (0.5, 1.4, 1.1), 7.0, 1.4), ("Top", (0.0, 0.0, 1.0), 3.0, 2.5))
    for name, direction, watts, scale in lights:
        data = bpy.data.lights.new(f"{parent.name} {name}", "AREA")
        data.shape = "DISK"
        data.size = size * scale * 0.5
        data.energy = watts
        light = bpy.data.objects.new(data.name, data)
        bpy.context.scene.collection.objects.link(light)
        light.parent = parent
        light.location = Vector(direction).normalized() * size * 2.2
        light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()


def camera_rig(name, center, azimuth_deg, elevation_deg, distance, lens=50):
    """Camera on an empty at center; azimuth 0 looks from the player side (-Y)."""
    rig = empty(f"{name} rig")
    rig.location = center
    rig.rotation_euler.z = math.radians(azimuth_deg)
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    cam.parent = rig
    e = math.radians(elevation_deg)
    cam.location = (0, -distance * math.cos(e), distance * math.sin(e))
    cam.rotation_euler = (math.pi / 2 - e, 0, 0)
    add_lights(rig, 0.18)
    return rig, cam


def world_setup(scene):
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb((0.80, 0.80, 0.82)), 1)
    bg.inputs["Strength"].default_value = 0.6
    scene.world = world
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"


def setup_render(scene, cycles, res=(1920, 1080), samples=64):
    scene.render.engine = "CYCLES" if cycles else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoising_use_gpu = True
    scene.render.use_persistent_data = True
    image = scene.render.image_settings
    image.media_type = "IMAGE"
    image.file_format = "PNG"
    image.color_mode = "RGB"
    if cycles:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.refresh_devices()
        for device in prefs.get_devices_for_type("METAL"):
            device.use = device.type != "CPU"
        scene.cycles.device = "GPU"


def use_rig(scene, rig, cam):
    scene.camera = cam
    for light in (o for o in scene.objects if o.type == "LIGHT"):
        light.hide_render = light.parent != rig


def render_still(scene, frame, path):
    scene.frame_set(frame)
    scene.render.filepath = str(path)
    started = time.monotonic()
    bpy.ops.render.render(write_still=True)
    print(f"[eink] wrote {path} in {time.monotonic() - started:.1f} s")


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    world_setup(scene)
    mats = {
        "red": pla("PLA red", RED),
        "black": pla("PLA black", BLACK),
        "floor": material("Desk", (0.78, 0.78, 0.80), roughness=0.8),
        "fr4": material("Milled FR4", FR4, roughness=0.62),
        "copper": material("Bare copper", COPPER, roughness=0.28, metallic=1.0),
        "header": material("Header nylon", (0.05, 0.05, 0.05), roughness=0.5),
        "eink": material("E-ink paper", EINK, roughness=0.7),
        "keycap": material("Keycap PBT", (0.80, 0.80, 0.78), roughness=0.55),
        "fpc": material("FPC connector", (0.22, 0.22, 0.22), roughness=0.4),
        "pouch": material("LiPo pouch", (0.70, 0.71, 0.73), roughness=0.35, metallic=0.7),
        "enig": material("ENIG", (0.93, 0.78, 0.45), roughness=0.25, metallic=1.0),
        "mask": material("Black mask", (0.03, 0.03, 0.035), roughness=0.45, coat=0.3),
        "steel": material("Stainless", (0.62, 0.62, 0.64), roughness=0.28, metallic=1.0),
        "brass": material("Brass insert", (0.80, 0.62, 0.32), roughness=0.3, metallic=1.0),
    }
    pivots = build(mats)
    add_floor(mats)
    explode = MODE in ("explode", "check", "hero")
    if explode:
        key_explode(pivots)
    bpy.context.view_layer.update()

    parts = [o for o in scene.objects if o.type == "MESH" and o.name != "Desk"]
    low, high = bounds(parts)
    print(f"[eink] assembled bbox mm {[round(v / MM, 2) for v in (*low, *high)]}")
    center = (low + high) / 2
    exp_frame = 1 + round(EXPLODED_AT * FPS)
    if explode:
        scene.frame_set(exp_frame)
        e_low, e_high = bounds(parts)
        print(f"[eink] exploded bbox mm {[round(v / MM, 2) for v in (*e_low, *e_high)]}")
        scene.frame_set(1)
        e_center = (e_low + e_high) / 2

    if MODE == "turntable":
        rig, cam = camera_rig("Turntable", center, TURN_START_DEG, ELEVATION_DEG, 0.42)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        frames = round(TURN_SECONDS * FPS)
        rig.keyframe_insert("rotation_euler", index=2, frame=1)
        rig.rotation_euler.z += 2 * math.pi
        rig.keyframe_insert("rotation_euler", index=2, frame=frames + 1)  # == frame 1
        use_rig(scene, rig, cam)
        setup_render(scene, True)
        scene.frame_start, scene.frame_end = 1, frames
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "turntable.blend"))
        return
    if MODE == "explode":
        rig, cam = camera_rig("Explode", e_center, -55, 20, 0.62)
        frames = round(EXPLODE_SECONDS * FPS)
        # Gentle sway that ends where it starts, so the loop is seamless
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        base = rig.rotation_euler.z
        for f in range(1, frames + 2, 10):
            rig.rotation_euler.z = base + math.radians(14) * math.sin(2 * math.pi * (f - 1) / frames)
            rig.keyframe_insert("rotation_euler", index=2, frame=f)
        # Dolly out while the parts are apart, back in as they close up
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
        e = math.radians(20)
        for seconds, apart in ((0, 0), (0.3, 0), (3.0, 1), (5.0, 1), (7.7, 0), (EXPLODE_SECONDS, 0)):
            distance = 0.44 + (0.62 - 0.44) * apart
            cam.location = (0, -distance * math.cos(e), distance * math.sin(e))
            cam.keyframe_insert("location", frame=1 + round(seconds * FPS))
            rig.location = center.lerp(e_center, apart)
            rig.keyframe_insert("location", frame=1 + round(seconds * FPS))
        use_rig(scene, rig, cam)
        setup_render(scene, True)
        scene.frame_start, scene.frame_end = 1, frames
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "explode.blend"))
        return

    cycles = MODE == "hero"
    out = MEDIA if cycles else CHECK
    out.mkdir(parents=True, exist_ok=True)
    setup_render(scene, cycles, samples=128)
    shots = {
        "hero": (center, -35, 22, 0.40, 1),
        "exploded": (e_center, -55, 20, 0.62, exp_frame),
    }
    if not cycles:
        shots.update({
            "front": (center, 0, 12, 0.36, 1), "left": (center, -90, 10, 0.36, 1),
            "back": (center, 160, 25, 0.36, 1), "top": (center, -20, 70, 0.40, 1),
            "exploded-side": (e_center, -90, 10, 0.55, exp_frame),
            "exploded-back": (e_center, 145, 25, 0.55, exp_frame),
        })
    for name, (c, az, el, dist, frame) in shots.items():
        rig, cam = camera_rig(name, c, az, el, dist)
        use_rig(scene, rig, cam)
        render_still(scene, frame, out / f"{name}.png")


main()
