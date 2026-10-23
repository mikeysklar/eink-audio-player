"""8 s turntable of the eink-audio-player board with an exploded view.

    blender -b --factory-startup --python turntable.py                # Cycles (Metal GPU) 1080x1080 MP4
    blender -b --factory-startup --python turntable.py -- --preview   # EEVEE 540x540 MP4
    blender -b --factory-startup --python turntable.py -- --still     # EEVEE PNGs + .blend
    blender -b --factory-startup --python turntable.py -- --hero      # Cycles (Metal GPU) hero PNGs
    blender -b --factory-startup --python turntable.py -- --save      # scene .blend only, for render_parallel.sh

Set CAD_DIR to the folder export.sh wrote, and OUT_DIR for the renders (default: ./cad and ./out
next to this file). Loads cad/*.glb: the board, then one GLB per part, board bbox bottom-left
origin, Y up. The board stands upright, display and keys on the front. The camera orbits once
while the breakouts lift off their sockets on the back and the battery, e-ink and NeoKey drop
away from the front.

Board frame: KiCad mm, Y up, F.Cu face at Z=1.6, back-side parts at negative Z.
"""

import math
import os
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
CAD = Path(os.environ.get("CAD_DIR", HERE / "cad"))
OUT = Path(os.environ.get("OUT_DIR", HERE / "out"))
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / "eink-audio-player-turntable.blend"
OUTPUT = OUT / "board-turntable.mp4"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILL = "--still" in ARGS
HERO = "--hero" in ARGS
SAVE = "--save" in ARGS
PREVIEW = "--preview" in ARGS or STILL
MM = 0.001

FPS = 30
DURATION = 8.0  # seconds of video
FRAMES = round(DURATION * FPS)
SIZE = 1080  # square frame; PREVIEW renders at half this
START_DEG = 225  # t=0 looks at the front (display, keys) from 45 degrees left
ELEVATION_DEG = 16
# The timings below are written for a 15 s clip; frame_at() squeezes them into DURATION.
TIMING = DURATION / 15


def frame_at(seconds):
    return 1 + round(seconds * TIMING * FPS)


# group -> (board-Z offset mm, (out start, out end) s, (back start, back end) s)
MOVES = {
    "feather": (24, (4.0, 6.0), (12.6, 14.5)),
    "tlv": (24, (4.2, 6.2), (12.4, 14.3)),
    "eyespi": (20, (4.4, 6.4), (12.2, 14.1)),
    "sockets": (9, (4.8, 6.8), (12.0, 13.6)),
    "battery": (-11, (4.0, 6.0), (12.6, 14.5)),
    "display": (-26, (4.2, 6.5), (12.3, 14.4)),
    "neokey": (-26, (4.4, 6.7), (12.2, 14.3)),
    "keycaps": (-12, (5.0, 7.0), (11.8, 13.4)),
}
# group -> references exported by export.sh
GROUPS = {
    "feather": ["A1"], "tlv": ["A3"], "eyespi": ["A7"],
    "sockets": ["J1", "J2", "J4", "J5", "J9", "J10"],
    "fixed": ["SW1", "R1", "R2", "R3", "R4"],
    "battery": ["BT1"], "display": ["DS1"], "neokey": ["A5"],
}
# Male header strips under the Feather and TLV (their STEPs have none): socket -> group
HEADERS = {"J1": "feather", "J2": "feather", "J9": "tlv", "J10": "tlv"}
SOCKET_TOP, BREAKOUT_BOTTOM = 9.0, 11.49

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


def import_glb(name):
    """Import one GLB; returns (top-level objects, mesh objects)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(CAD / f"{name}.glb"))
    new = [obj for obj in bpy.data.objects if obj not in before]
    return [obj for obj in new if obj.parent is None], [obj for obj in new if obj.type == "MESH"]


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


def smooth(meshes):
    for obj in meshes:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
    if meshes:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    bpy.ops.object.select_all(action="DESELECT")


def bounds(objects):
    points = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
    low = Vector(min(p[i] for p in points) for i in range(3))
    high = Vector(max(p[i] for p in points) for i in range(3))
    return low, high


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def header_strip(ref, mats):
    """Black 2.5 mm male-header spacer on top of a socket, with the socket's length."""
    low, high = bounds([o for o in GLB_MESHES[ref]])
    y = (low.y + high.y) / 2 / MM
    x0, x1 = low.x / MM + 0.1, high.x / MM - 0.1
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = f"Header {ref}"
    obj.scale = ((x1 - x0) * MM, 2.5 * MM, (BREAKOUT_BOTTOM - SOCKET_TOP) * MM)
    obj.location = ((x0 + x1) / 2 * MM, y * MM, (SOCKET_TOP + BREAKOUT_BOTTOM) / 2 * MM)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mats["header"])
    return obj


GLB_MESHES = {}


def build(mats):
    root = empty("Assembly")  # board frame -> world: stood upright, centred
    done = set()
    board_top, board_meshes = import_glb("board")
    for obj in board_meshes:
        z0 = min((obj.matrix_world @ Vector(c)).z for c in obj.bound_box)
        obj.data.materials.clear()
        obj.data.materials.append(mats["copper"] if z0 > 1.0 * MM else mats["fr4"])
    for obj in board_top:
        obj.parent = root
    smooth(board_meshes)

    pivots = {name: empty(f"Explode {name}", root) for name in list(MOVES) + ["fixed"]}
    for group, refs in GROUPS.items():
        for ref in refs:
            top, meshes = import_glb(ref)
            GLB_MESHES[ref] = meshes
            fix_materials(meshes, done)
            smooth(meshes)
            for obj in top:
                obj.parent = pivots[group]
    for ref, group in HEADERS.items():
        header_strip(ref, mats).parent = pivots[group]

    # The four MX switch + keycap blocks (Cherry MX keycap.wrl) drop further off the NeoKey
    keys = [obj for obj in GLB_MESHES["A5"] if obj.name.startswith("=>[0:1:1:18]")]
    pivots["keycaps"].parent = pivots["neokey"]
    for obj in keys:
        world = obj.matrix_world.copy()
        obj.parent = pivots["keycaps"]
        obj.matrix_world = world
    print(f"[eink-audio-player] {len(keys)} key blocks")

    recolor(GLB_MESHES["DS1"], (0.56, 0.66, 0.56), mats["eink"])  # KiCad's grey-green -> paper
    recolor(GLB_MESHES["A5"], (0.79, 0.79, 0.75), mats["keycap"])
    recolor(GLB_MESHES["BT1"], None, mats["pouch"])
    for obj in GLB_MESHES["A7"]:  # hand-made EYESPI STEP has no colours
        name = obj.name.lower()
        obj.data.materials.clear()
        obj.data.materials.append(mats["mask"] if "board" in name else
                                  mats["fpc"] if "fpc" in name else mats["header"])
        print(f"[eink-audio-player] A7 mesh {obj.name} -> {obj.data.materials[0].name}")
    for ref in ("A1", "A3", "A5", "DS1"):  # Adafruit's olive CAD boards -> black mask, ENIG pads
        recolor(GLB_MESHES[ref], (0.188, 0.156, 0.061), mats["mask"])
        recolor(GLB_MESHES[ref], (0.96, 0.66, 0.40), mats["enig"])

    for name, (offset, out, back) in MOVES.items():
        key_move(pivots[name], offset, out, back)
    return root, board_meshes


def recolor(meshes, linear_rgb, mat):
    """Swap every material slot whose base colour is linear_rgb (None: all) for mat."""
    for obj in meshes:
        for slot in obj.material_slots:
            col = slot.material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            if linear_rgb is None or all(abs(col[i] - linear_rgb[i]) < 0.02 for i in range(3)):
                slot.material = mat


def key_move(obj, offset_mm, out, back):
    for seconds, z in ((out[0], 0), (out[1], offset_mm), (back[0], offset_mm), (back[1], 0)):
        obj.location = (0, 0, z * MM)
        obj.keyframe_insert("location", index=2, frame=frame_at(seconds))


def fcurves(obj):
    action = obj.animation_data.action
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def add_lights(parent, size):
    """Softboxes that turn with the camera, so every side is lit the same."""
    lights = (("Key", (-1.0, -1.2, 1.1), 2.4, 2.0), ("Fill", (1.3, -0.8, 0.3), 0.9, 2.5),
              ("Rim", (0.6, 1.4, 0.9), 2.0, 1.5), ("Under", (-0.4, -0.6, -1.2), 0.4, 2.0))
    for name, direction, watts, scale in lights:
        data = bpy.data.lights.new(name, "AREA")
        data.shape = "DISK"
        data.size = size * scale * 0.5
        data.energy = watts
        light = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(light)
        light.parent = parent
        light.location = Vector(direction).normalized() * size * 2.2
        light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()


def add_turntable(center, near, far):
    """Camera on an empty that turns once; it dollies out while the parts are apart."""
    spin = empty("Turntable")
    spin.location = center
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    bpy.context.scene.collection.objects.link(camera)
    camera.data.lens = 50
    camera.data.clip_start = 0.001
    camera.data.shift_y = -0.04  # looking down, the parts sit low in frame; recentre them
    camera.parent = spin
    elevation = math.radians(ELEVATION_DEG)
    camera.rotation_euler = (math.pi / 2 - elevation, 0, 0)
    for seconds, distance in ((0, near), (3.6, near), (6.6, far), (12.0, far), (14.8, near), (15, near)):
        camera.location = (0, -distance * math.cos(elevation), distance * math.sin(elevation))
        camera.keyframe_insert("location", frame=frame_at(seconds))
    start = math.radians(START_DEG)
    spin.rotation_euler.z = start
    spin.keyframe_insert("rotation_euler", index=2, frame=1)
    spin.rotation_euler.z = start + 2 * math.pi
    spin.keyframe_insert("rotation_euler", index=2, frame=FRAMES + 1)  # last frame == frame 1
    for fcurve in fcurves(spin):
        for point in fcurve.keyframe_points:
            point.interpolation = "LINEAR"
    bpy.context.scene.camera = camera
    add_lights(spin, far / 2.2)  # same softbox geometry as the still rigs
    return spin, camera


def world_setup(scene):
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.012, 0.014, 1)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"


def setup_output(scene):
    if PREVIEW:
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = scene.render.resolution_y = SIZE // 2
    else:
        scene.render.engine = "CYCLES"
        scene.render.resolution_x = scene.render.resolution_y = SIZE
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
        scene.cycles.denoising_use_gpu = True
        scene.render.use_persistent_data = True
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES
    image = scene.render.image_settings
    image.media_type = "IMAGE"
    image.file_format = "PNG"
    image.color_mode = "RGB"


def use_gpu(scene):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.refresh_devices()
    for device in prefs.get_devices_for_type("METAL"):
        device.use = device.type != "CPU"
    scene.cycles.device = "GPU"


def still_camera(scene, name, azimuth_deg, elevation_deg, center, distance, lens=50):
    """A fixed camera for stills; azimuth 0 looks at the back (component side)."""
    rig = empty(f"{name} rig")
    rig.location = center
    rig.rotation_euler.z = math.radians(azimuth_deg)
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.001
    cam.parent = rig
    e = math.radians(elevation_deg)
    cam.location = (0, -distance * math.cos(e), distance * math.sin(e))
    cam.rotation_euler = (math.pi / 2 - e, 0, 0)
    add_lights(rig, distance / 2.2 * 1.0)
    return cam


def render_still(scene, camera, frame, path):
    scene.camera = camera
    for light in (o for o in scene.objects if o.type == "LIGHT"):
        light.hide_render = light.parent != camera.parent  # each rig brings its own softboxes
    scene.frame_set(frame)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[eink-audio-player] wrote {path}")


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    world_setup(scene)
    mats = {
        "fr4": material("Milled FR4", FR4, roughness=0.62),
        "copper": material("Bare copper", COPPER, roughness=0.28, metallic=1.0),
        "header": material("Header nylon", (0.05, 0.05, 0.05), roughness=0.5),
        "eink": material("E-ink paper", EINK, roughness=0.7),
        "keycap": material("Keycap PBT", (0.74, 0.73, 0.70), roughness=0.55),
        "fpc": material("FPC connector", (0.22, 0.22, 0.22), roughness=0.4),
        "pouch": material("LiPo pouch", (0.70, 0.71, 0.73), roughness=0.35, metallic=0.7),
        "enig": material("ENIG", (0.93, 0.78, 0.45), roughness=0.25, metallic=1.0),
        "mask": material("Black mask", (0.03, 0.03, 0.035), roughness=0.45, coat=0.3),
    }
    root, board_meshes = build(mats)

    # Stand the board up: board Y -> world Z, front (board -Z) -> world +Y
    low, high = bounds(board_meshes)
    mid = (low + high) / 2
    root.matrix_world = Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Translation(-mid)
    bpy.context.view_layer.update()

    parts = [o for o in scene.objects if o.type == "MESH"]
    scene.frame_set(1)
    a_low, a_high = bounds(parts)
    scene.frame_set(frame_at(9.0))
    e_low, e_high = bounds(parts)
    scene.frame_set(1)
    center = (e_low + e_high) / 2
    center.z = (a_low.z + a_high.z) / 2

    half_frame = 18 / 50  # square frame: 36 mm sensor, 50 mm lens, half-width per unit distance

    def fit(low, high):
        # The widest horizontal extent at any orbit angle, and the height, both fit the frame
        r = max(Vector((x, y)).length for x in (low.x - center.x, high.x - center.x)
                for y in (low.y - center.y, high.y - center.y))
        h = (high.z - low.z) / 2
        return max(r / half_frame * 1.22, h / half_frame * 1.22)

    near, far = fit(a_low, a_high), fit(e_low, e_high)
    print(f"[eink-audio-player] assembled {(a_high - a_low) / MM} mm, exploded {(e_high - e_low) / MM} mm, "
          f"camera {near / MM:.0f} -> {far / MM:.0f} mm")
    spin, camera = add_turntable(center, near, far)
    setup_output(scene)
    if not PREVIEW:
        use_gpu(scene)  # Cycles on the Metal GPU
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    if SAVE:  # scene only; final frames come from render_parallel.sh on this .blend
        return

    if STILL or HERO:
        size = near
        stills = {
            "front": still_camera(scene, "Front", 180, 8, center, size * 0.75),
            "back": still_camera(scene, "Back", 0, 8, center, size * 0.75),
            "iso": still_camera(scene, "Iso", 215, 28, center, size * 0.8),
            "exploded": still_camera(scene, "Exploded", 55, 14, center, far * 1.05),
        }
        tag = "hero" if HERO else "still"
        for name in (("iso", "exploded") if HERO else stills):
            frame = frame_at(9.0) if name == "exploded" else 1
            render_still(scene, stills[name], frame, OUT / f"{tag}-{name}.png")
        if not HERO:  # and two turntable frames
            for seconds in (2.0, 9.5):
                render_still(scene, camera, frame_at(seconds), OUT / f"still-turntable-{seconds:04.1f}s.png")
        return

    image = scene.render.image_settings
    image.media_type = "VIDEO"
    image.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = str(OUTPUT.with_suffix("")) + "-"
    started = time.monotonic()
    bpy.ops.render.render(animation=True)
    written = sorted(OUT.glob(OUTPUT.stem + "-*.mp4"), key=os.path.getmtime)
    if written:
        os.replace(written[-1], OUTPUT)
    print(f"[eink-audio-player] wrote {OUTPUT} in {time.monotonic() - started:.0f} s")


main()
