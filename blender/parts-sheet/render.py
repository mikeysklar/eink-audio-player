# Renders parts-sheet and assembly for the eink-audio-player stand.
# Run: Blender -b --factory-startup --python render.py -- <mode> <out.png>
import bpy, sys, os, json
from mathutils import Matrix, Vector
from math import radians

# Inputs. Printed parts are STL files exported from the arcade FreeCAD model.
# Board and key meshes are optional; they only appear in the assembly view.
D = "/Volumes/clear/Downloads/ada/hstx-audio/landing-pad/arcade/build"
BOARD_STL = "/private/tmp/claude-501/enc/mesh/stack.stl"
KEYS_STL = "/private/tmp/claude-501/enc/mesh/keys.stl"

mode, out = sys.argv[sys.argv.index("--") + 1:][:2]  # mode: sheet | assembly
RED = (0.85, 0.2, 0.3, 1.0)
BLACK = (0.08, 0.08, 0.09, 1.0)
GREY = (0.82, 0.82, 0.82, 1.0)
PCB_GREEN = (0.05, 0.35, 0.20, 1.0)
KEY_WHITE = (0.9, 0.9, 0.88, 1.0)
PARTS = ["chassis", "bezel", "deck", "cradle", "handle"]
RED_PARTS = ("chassis", "handle")
LABEL = {
    "chassis": "chassis (cheeks, feet, ANO mount)", "bezel": "bezel (display)",
    "deck": "deck (keys)", "cradle": "cradle (standoffs, battery)", "handle": "handle (snaps in)",
}
# Sheet spots (bbox centre on the ground, mm), and the hardware row at 4x
SPOT = {"chassis": (-150, 75), "bezel": (25, 95), "handle": (165, 95), "deck": (25, -45),
        "cradle": (165, -35)}
HW = [("screw6", "M2.5 x 6, 4 off"), ("screw8", "M2.5 x 8, 4 off"),
      ("screw16", "M2.5 x 16, 4 off"), ("insert", "heat insert, 12 off")]
HW_SCALE = 4.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.93, 0.93, 0.93)
scene.display.render_aa = "8"
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.cavity_ridge_factor = 0.5
scene.display.shading.cavity_valley_factor = 0.5
scene.render.resolution_x = 2000
scene.render.resolution_y = 1400
scene.render.film_transparent = False

def mat(name, col):
    m = bpy.data.materials.new(name)
    m.diffuse_color = col
    return m

m_red = mat("red", RED)
m_black = mat("black", BLACK)
m_grey = mat("grey", GREY)
m_pcb = mat("pcb", PCB_GREEN)
m_keys = mat("keys", KEY_WHITE)
m_steel = mat("steel", (0.55, 0.55, 0.58, 1.0))
m_brass = mat("brass", (0.80, 0.62, 0.32, 1.0))

def import_part(n):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(D, n + ".stl"))
    o = [x for x in bpy.data.objects if x not in before][0]
    o.name = n
    o.data.materials.clear()
    o.data.materials.append(m_red if n in RED_PARTS else m_black)
    return o


def import_hw(kind, m):
    bpy.ops.wm.stl_import(filepath=os.path.join(D, "hw_%s.stl" % kind))
    o = bpy.context.selected_objects[0]
    o.data.materials.clear()
    o.data.materials.append(m)
    return o

def label(text, loc, size):
    bpy.ops.object.text_add(location=loc)
    t = bpy.context.object
    t.data.body = text
    t.data.size = size
    t.data.extrude = 0.0
    t.data.align_x = "LEFT"
    t.data.align_y = "BOTTOM"
    t.data.materials.append(m_grey)
    t.data.materials.clear()
    t.data.materials.append(bpy.data.materials.get("black"))
    return t

def center_xy_on_ground(o, cx, cy):
    # Move object so its bbox centre sits at (cx, cy), lowest point at z=0
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    c = (mn + mx) / 2
    o.location += Vector((cx, cy, 0)) - Vector((c.x, c.y, mn.z))
    return mx - mn

def ortho_cam(target, direction, size):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = target + direction.normalized() * 1000
    look = target - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam

def sun():
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 500))
    bpy.context.object.data.energy = 0

if mode == "sheet":
    for n in PARTS:
        o = import_part(n)
        cx, cy = SPOT[n]
        dims = center_xy_on_ground(o, cx, cy)
        label(LABEL[n], (cx - 60, cy - dims.y / 2 - 22, 0), 10.0)
    for i, (kind, text) in enumerate(HW):
        o = import_hw(kind, m_brass if kind == "insert" else m_steel)
        o.scale = (HW_SCALE,) * 3
        o.rotation_euler = (radians(90), 0, 0)   # lying down, head to the back
        bpy.context.view_layer.update()
        cx, cy = -150 + i * 85, -170
        center_xy_on_ground(o, cx, cy)
        label(text, (cx - 40, cy - 45, 0), 9.0)
    label("(hardware shown 4x)", (65, -230, 0), 9.0)
    # Shared iso-like camera from front-left, top-down bias
    target = Vector((-35, -40, 0))
    ortho_cam(target, Vector((-0.7, -1.0, 0.85)), 560)
else:
    for n in PARTS:
        import_part(n)
    for path, m, name in ((BOARD_STL, m_pcb, "stack"), (KEYS_STL, m_keys, "keys")):
        bpy.ops.wm.stl_import(filepath=path)
        o = bpy.context.selected_objects[0]
        o.name = name
        o.data.materials.clear()
        o.data.materials.append(m)
    for item in json.load(open(os.path.join(D, "fasteners.json"))):
        o = import_hw(item["kind"], m_brass if item["kind"] == "insert" else m_steel)
        o.matrix_world = Matrix.Translation(Vector(item["p"])) @ \
            Vector((0, 0, -1)).rotation_difference(Vector(item["axis"])).to_matrix().to_4x4()
    target = Vector((18, -5, 35))    # the ANO mount reaches out to x 84, y -71
    ortho_cam(target, Vector((-1.0, -1.1, 0.8)), 250)

bpy.ops.object.light_add(type="SUN", location=(0, 0, 0))
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out)
