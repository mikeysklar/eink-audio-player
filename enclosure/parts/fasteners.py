# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Hardware: the twelve M2.5 socket head screws and the twelve heat inserts they go into,
# placed in world mm. Writes
#   build/fasteners.json   one entry per item: kind, length, p (screw: under the head;
#                          insert: its top face), axis (the way the screw goes in), and the
#                          part or board it rides on in the renders
#   build/hw_<kind>.stl    each kind once, in its own frame: p at the origin, axis -Z
#   build/fasteners.step   everything placed, for the FCStd
#   build/fasteners_check.brep  what assemble_arcade.py clashes: heads full size, shanks
#                          and inserts shrunk to their holes' cores (2.0 and 3.0)
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import math
import os
import FreeCAD as App
import Part
import Mesh
import arcade_common as ac

L = ac.layout()
D = json.load(open(os.path.join(ac.HERE, "inputs", "measure_display.json")))
NK = json.load(open(os.path.join(ac.HERE, "inputs", "measure_neokey_sw1.json")))["neokey"]
X_IN, X_OUT = L["x_in"], L["x_in"] + L["cheek_t"]
HEAD_D, HEAD_H, SHANK_D = 4.5, 2.5, 2.5
CB_D = 1.5                                           # cheek counterbore depth
BACK = D["outer_face_z"]["pcb"] - 0.05               # bezel back face, board frame
items = []


def add(kind, length, p, axis, rides):
    a = App.Vector(*axis).normalize()
    items.append({"kind": kind, "length": length, "p": [round(v, 4) for v in p],
                  "axis": [round(v, 6) for v in a], "rides": rides})


def world_dir(body, d):
    m = ac._matrix(body)
    return m.multVec(App.Vector(*d)) - m.multVec(App.Vector(0, 0, 0))


# Cheek joints: under the head is the counterbore floor; the insert is in the boss end.
for side, sx in (("L", -1), ("R", 1)):
    for joint, part in (("bezel_top", "bezel"), ("deck_front", "deck")):
        _, y, z = L["joints"][joint + "_" + side]
        add("screw8", 8, (sx * (X_OUT - CB_D), y, z), (-sx, 0, 0), "chassis")
        add("insert", ac.INSERT_LEN, (sx * (X_IN - ac.END_GAP), y, z), (-sx, 0, 0), part)

# Stack: from the board's copper side through H1-H4, the cradle and the display, into the
# bezel's inserts.
down = world_dir("stack", (0, 0, -1))
for hx, hy in D["pcb"]["holes"]:
    add("screw16", 16, ac.stack_pt((hx, hy, 1.6)), down, "board")
    add("insert", ac.INSERT_LEN, ac.stack_pt((hx, hy, BACK)), down, "bezel")

# NeoKey: from its back into the deck's two insert standoffs (deck.py SCREWED).
holes = sorted((h["x"], h["y"]) for h in NK["holes"])
up = world_dir("keys", (0, 0, -1))
for x, y in (holes[0], holes[-1]):
    add("screw6", 6, ac.keys_pt((x, y, NK["pcb_z"][1])), up, "keys")
    add("insert", ac.INSERT_LEN, ac.keys_pt((x, y, NK["key_face_z"] - 0.05)), up, "deck")

# ANO: from its wheel side into the mount's two insert standoffs (ano_mount.py SCREWED).
deg = math.radians(L["deck_deg"])
EX = App.Vector(0, math.cos(deg), math.sin(deg))
EY = App.Vector(1, 0, 0)
EZ = App.Vector(0, math.sin(deg), -math.cos(deg))
CENTRE = App.Vector(X_OUT + 20.32, -54.0, 14.07)
for u, v in ((-15.24, -17.78), (15.24, 17.78)):
    add("screw6", 6, CENTRE + EX * u + EY * v - EZ * 0.06, EZ, "ano")   # on the pad ring
    add("insert", ac.INSERT_LEN, CENTRE + EX * u + EY * v + EZ * 1.62, EZ, "chassis")


def screw(length, shank_d=SHANK_D):
    """Socket head cap screw, under the head at the origin, shank down -Z."""
    head = Part.makeCylinder(HEAD_D / 2, HEAD_H)
    head = head.makeChamfer(0.3, [e for e in head.Edges if e.BoundBox.ZMin > HEAD_H - 0.01])
    hexa = Part.Face(Part.makePolygon([App.Vector(1.15 * math.cos(math.radians(a)),
                                                  1.15 * math.sin(math.radians(a)), HEAD_H - 1.3)
                                       for a in range(0, 361, 60)])).extrude(App.Vector(0, 0, 2))
    shank = Part.makeCylinder(shank_d / 2, length, App.Vector(0, 0, -length))
    shank = shank.makeChamfer(0.25, [e for e in shank.Edges if e.BoundBox.ZMax < -length + 0.01])
    return head.cut(hexa).fuse(shank).removeSplitter()


def insert(od=ac.INSERT_OD, bore=True):
    """Knurled brass insert, top face at the origin, body down -Z."""
    body = Part.makeCylinder(od / 2, ac.INSERT_LEN, App.Vector(0, 0, -ac.INSERT_LEN))
    if bore:
        for z in (-1.0, -2.3):
            ring = Part.makeCylinder(od / 2 + 1, 0.45, App.Vector(0, 0, z)).cut(
                Part.makeCylinder(od / 2 - 0.2, 0.45, App.Vector(0, 0, z)))
            body = body.cut(ring)
        body = body.cut(Part.makeCylinder(SHANK_D / 2 - 0.05, 10, App.Vector(0, 0, -5)))
    return body.removeSplitter()


def place(shape, p, axis):
    s = shape.copy()
    rot = App.Rotation(App.Vector(0, 0, -1), App.Vector(*axis))
    s.Placement = App.Placement(App.Vector(*p), rot)
    return s


protos = {"screw6": screw(6), "screw8": screw(8), "screw16": screw(16), "insert": insert()}
check = {"screw6": screw(6, 2.0), "screw8": screw(8, 2.0), "screw16": screw(16, 2.0),
         "insert": insert(3.0, bore=False)}
for kind, s in protos.items():
    Mesh.Mesh(s.tessellate(0.02)).write(os.path.join(ac.BUILD, "hw_%s.stl" % kind))
placed = [place(protos[i["kind"]], i["p"], i["axis"]) for i in items]
Part.makeCompound(placed).exportStep(os.path.join(ac.BUILD, "fasteners.step"))
Part.makeCompound([place(check[i["kind"]], i["p"], i["axis"]) for i in items]).exportBrep(
    os.path.join(ac.BUILD, "fasteners_check.brep"))
json.dump(items, open(os.path.join(ac.BUILD, "fasteners.json"), "w"), indent=1)
count = {}
for i in items:
    count[i["kind"]] = count.get(i["kind"], 0) + 1
print("fasteners:", count)
