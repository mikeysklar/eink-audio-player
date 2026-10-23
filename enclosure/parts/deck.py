# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
# Key deck: the MX switch plate (1.5 thick, top 5.0 off the NeoKey face, 14.1 holes), four
# standoffs the NeoKey screws up into, a rib along the front edge (the back edge meets the
# bezel chin, so it has none), and end bosses for the cheeks. Built flat in the NeoKey's
# board frame (keys on -Z) and moved to world.
# Print standing on the back edge (y = Y1 face, flat): the key holes then bridge 14 mm.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import os
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
NK = json.load(open(os.path.join(ac.HERE, "inputs", "measure_neokey_sw1.json")))["neokey"]
FACE = NK["key_face_z"]                              # -12.115
BX_L, BX_R = 30.53 + L["x_in"], 30.53 - L["x_in"]
JY_FRONT, JY_BACK = 7.0, 29.8                        # layout.py deck joints
JZ = FACE - 4.25                                     # plate mid-plane
BOSS_R, BOSS_LEN = 3.0, 8.0
PILOT_D, PILOT_DEPTH = 2.2, 6.0
PL_TOP, PL_BOT = FACE - 5.0, FACE - 3.5              # plate faces, -17.115 / -15.615
Y0, Y1 = JY_FRONT - BOSS_R, JY_BACK + BOSS_R
HOLE = 14.1
SO_R = 2.2                                           # standoff, od 4.4
RIB_W, RIB_D = 1.6, 1.6                              # 0.3 above the front foot bar
X_AXIS = App.Vector(1, 0, 0)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


shape = box(BX_R, BX_L, Y0, Y1, PL_TOP, PL_BOT)
shape = shape.fuse(box(BX_R, BX_L, Y0, Y0 + RIB_W, PL_BOT - 0.01, PL_BOT + RIB_D))
for y in (JY_FRONT, JY_BACK):
    shape = shape.fuse(Part.makeCylinder(BOSS_R, BOSS_LEN, App.Vector(BX_R, y, JZ), X_AXIS))
    shape = shape.fuse(Part.makeCylinder(BOSS_R, BOSS_LEN, App.Vector(BX_L - BOSS_LEN, y, JZ),
                                         X_AXIS))
for h in NK["holes"]:
    shape = shape.fuse(Part.makeCylinder(SO_R, FACE - 0.05 - (PL_BOT - 0.01),
                                         App.Vector(h["x"], h["y"], PL_BOT - 0.01)))
for x, y in NK["key_centres"]:
    shape = shape.cut(box(x - HOLE / 2, x + HOLE / 2, y - HOLE / 2, y + HOLE / 2,
                          PL_TOP - 1, PL_BOT + 1))
for h in NK["holes"]:
    shape = shape.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH,
                                        App.Vector(h["x"], h["y"], FACE + 1 - PILOT_DEPTH)))
for y in (JY_FRONT, JY_BACK):
    shape = shape.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH + 1,
                                        App.Vector(BX_R - 1, y, JZ), X_AXIS))
    shape = shape.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH + 1,
                                        App.Vector(BX_L - PILOT_DEPTH, y, JZ), X_AXIS))

shape = shape.removeSplitter()
shape.transformShape(ac._matrix("keys"))
shape = ac.save(shape, "deck")
ac.clash(shape)
