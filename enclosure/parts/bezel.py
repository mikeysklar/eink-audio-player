# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Screen bezel: a frame over the e-ink, two stiles down the sides to the cheeks, and a
# chin under the board's bottom edge that the tilted stack rests on. The stack hangs off
# it: four M2.5 x 16 from the board side, through the board, the cradle and the display,
# into heat inserts in its back. It slides into the chassis from the front, its bottom
# bosses' pegs dropping into the cheek slots, and one M2.5 x 8 per side at the top bosses
# holds it. Built flat in the board frame (front face at z=FRONT, the player side) and
# moved to world. Print front face down.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import os
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
D = json.load(open(os.path.join(ac.HERE, "inputs", "measure_display.json")))
XE = L["x_in"] - ac.END_GAP                         # ends 0.25 off the cheeks
BX_L, BX_R = 30.53 + XE, 30.53 - XE                # board x at world x = -39.25 / +39.25
JY_TOP, JY_BOT, JZ = 73.57, 5.0, -12.35              # layout.py bezel joints
BOSS_R, BOSS_LEN = 3.0, 8.0
PILOT_D, PILOT_DEPTH = 2.2, 6.0
FRONT = JZ - BOSS_R                                  # -15.35, flush with the bosses
BACK = D["outer_face_z"]["pcb"] - 0.05               # just off the display PCB front
GAP = 0.3

g = D["glass"]
a = D["active_area"]["bbox"]
fpc = D["fpc_connector"]
X_AXIS = App.Vector(1, 0, 0)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


# Frame plate over the display PCB.
plate = box(-3.0, 64.0, 35.5, 78.5, FRONT, BACK)
# Stiles: 6 x 6 bars from the chin to the top boss, ending flush at the cheeks.
stile_r = box(BX_R, BX_R + 6.0, -3.5, JY_TOP + 3.0, FRONT, JZ + BOSS_R)
stile_l = box(BX_L - 6.0, BX_L, -3.5, JY_TOP + 3.0, FRONT, JZ + BOSS_R)
# Chin: catches the board's bottom edge (y=0, z 0..1.6), GAP below it.
chin = box(BX_R, BX_L, -3.5, -GAP, FRONT, 3.0)
shape = plate.fuse([stile_r, stile_l, chin])
for y in (JY_TOP, JY_BOT):
    shape = shape.fuse(Part.makeCylinder(BOSS_R, BOSS_LEN, App.Vector(BX_R, y, JZ), X_AXIS))
    shape = shape.fuse(Part.makeCylinder(BOSS_R, BOSS_LEN, App.Vector(BX_L - BOSS_LEN, y, JZ),
                                         X_AXIS))

# Glass pocket, and room for the display's ribbon connector just proud of its PCB.
shape = shape.cut(box(g[0] - GAP, g[1] + GAP, g[2] - GAP, g[3] + GAP, g[4] - GAP, BACK + 1))
shape = shape.cut(box(fpc[0] - GAP, fpc[1] + GAP, fpc[2] - GAP, fpc[3] + GAP, fpc[4] - GAP,
                      BACK + 1))
# Window over the active area, straight through the lip, with a 45 deg chamfer to the front.
wx0, wx1, wy0, wy1 = a[0] - 0.5, a[1] + 0.5, a[2] - 0.5, a[3] + 0.5
CH = 1.5
shape = shape.cut(box(wx0, wx1, wy0, wy1, FRONT + CH - 0.01, BACK + 1))
# Wedge in a local frame (local y = depth toward the front, local z = board y), turned so
# local (x, y, z) -> board (x, z, FRONT + CH - y).
w = Part.makeWedge(wx0, 0, wy0, wy0 - (CH + 1), wx0 - (CH + 1),
                   wx1, CH + 1, wy1, wy1 + (CH + 1), wx1 + (CH + 1))
m = App.Matrix()
m.A11, m.A12, m.A13 = 1, 0, 0
m.A21, m.A22, m.A23 = 0, 0, 1
m.A31, m.A32, m.A33 = 0, -1, 0
m.A34 = FRONT + CH
w.transformShape(m)
shape = shape.cut(w)

# Display: heat inserts from the back face, blind, so the front stays clean.
for hx, hy in D["pcb"]["holes"]:
    shape = shape.cut(ac.insert_hole((hx, hy, BACK), (0, 0, -1), extra=0.4))

# Top bosses: heat inserts in the ends. Bottom bosses: pegs for the cheek slots.
shape = shape.cut(ac.insert_hole((BX_R, JY_TOP, JZ), (1, 0, 0)))
shape = shape.cut(ac.insert_hole((BX_L, JY_TOP, JZ), (-1, 0, 0)))
shape = shape.fuse(Part.makeCylinder(ac.STUB_D / 2, ac.STUB_LEN + 0.01,
                                     App.Vector(BX_R - ac.STUB_LEN, JY_BOT, JZ), X_AXIS))
shape = shape.fuse(Part.makeCylinder(ac.STUB_D / 2, ac.STUB_LEN + 0.01,
                                     App.Vector(BX_L - 0.01, JY_BOT, JZ), X_AXIS))

shape.transformShape(ac._matrix("stack"))
# The deck's back bosses tuck under the chin, and the deck drops in from straight above:
# clear the bosses, and the path above them, by GAP (world frame).
for side, sx in (("L", -1), ("R", 1)):
    jx, jy, jz = L["joints"]["deck_back_" + side]
    r, n = BOSS_R + GAP, BOSS_LEN + GAP + 1
    o = App.Vector(jx + sx, jy, jz)
    path = Part.makeCylinder(r, n, o, App.Vector(-sx, 0, 0)).fuse([
        Part.makeCylinder(r, n, o + App.Vector(0, 0, 40), App.Vector(-sx, 0, 0)),
        Part.makeBox(n, 2 * r, 40, App.Vector(min(o.x, o.x - sx * n), jy - r, jz))])
    shape = shape.cut(path)
shape = shape.removeSplitter()
shape = ac.save(shape, "bezel")
ac.clash(shape)
