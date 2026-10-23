# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Screen bezel: a frame over the e-ink, two stiles down the sides to the cheeks, and a
# chin under the board's bottom edge that the tilted stack rests on. The four display
# screws go through it (longer M2.5s into the brass standoffs), so it carries the stack.
# Built flat in the board frame (front face at z=FRONT, the player side) and moved to
# world. Print front face down.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import os
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
D = json.load(open(os.path.join(ac.HERE, "inputs", "measure_display.json")))
BX_L, BX_R = 30.53 + L["x_in"], 30.53 - L["x_in"]   # board x at world x = -39.5 / +39.5
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

# Display screws: 2.8 through, 4.8 x 2.0 counterbore from the front.
for hx, hy in D["pcb"]["holes"]:
    shape = shape.cut(Part.makeCylinder(1.4, 10, App.Vector(hx, hy, FRONT - 1)))
    shape = shape.cut(Part.makeCylinder(2.4, 3.0, App.Vector(hx, hy, FRONT - 1)))

# Pilots for the battery strap screws, from the stiles' back faces (battery_strap.py).
for x in (BX_R + 3.0, BX_L - 3.0):
    shape = shape.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH, App.Vector(x, 17.75,
                                        JZ + BOSS_R - PILOT_DEPTH + 1)))

# Pilots in the boss ends.
for y in (JY_TOP, JY_BOT):
    shape = shape.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH + 1,
                                        App.Vector(BX_R - 1, y, JZ), X_AXIS))
    shape = shape.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH + 1,
                                        App.Vector(BX_L - PILOT_DEPTH, y, JZ), X_AXIS))

shape.transformShape(ac._matrix("stack"))
# The deck's back bosses tuck under the chin: clear them by GAP (world frame).
for side, sx in (("L", -1), ("R", 1)):
    jx, jy, jz = L["joints"]["deck_back_" + side]
    shape = shape.cut(Part.makeCylinder(BOSS_R + GAP, BOSS_LEN + GAP + 1,
                                        App.Vector(jx + sx, jy, jz), App.Vector(-sx, 0, 0)))
shape = shape.removeSplitter()
shape = ac.save(shape, "bezel")
ac.clash(shape)
