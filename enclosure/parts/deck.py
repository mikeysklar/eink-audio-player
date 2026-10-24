# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Key deck: the MX switch plate (1.5 thick, top 5.0 off the NeoKey face, 14.1 holes), four
# standoffs, a rib along the front edge (the back edge meets the bezel chin, so it has
# none), and end bosses for the cheeks. Two diagonal standoffs take heat inserts for
# M2.5 x 6 screws from the NeoKey's back; the other two have pins through its holes. The
# deck drops into the chassis from above after the bezel: the back bosses' pegs go into
# the cheek slots, under the bezel chin, and one M2.5 x 8 per side holds the front bosses.
# Built flat in the NeoKey's board frame (keys on -Z) and moved to world.
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
XE = L["x_in"] - ac.END_GAP
BX_L, BX_R = 30.53 + XE, 30.53 - XE
JY_FRONT, JY_BACK = 7.0, 29.8                        # layout.py deck joints
JZ = FACE - 4.25                                     # plate mid-plane
BOSS_R, BOSS_LEN = 3.0, 8.0
PILOT_D, PILOT_DEPTH = 2.2, 6.0
PL_TOP, PL_BOT = FACE - 5.0, FACE - 3.5              # plate faces, -17.115 / -15.615
Y0, Y1 = JY_FRONT - BOSS_R, JY_BACK + BOSS_R
HOLE = 14.1
SO_R, SO_R_INSERT = 2.2, 2.75                        # pin standoffs od 4.4, insert ones 5.5
PIN_D, PIN_LEN = 2.2, 1.4                            # into the NeoKey's 2.5 holes
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
HOLES = sorted((h["x"], h["y"]) for h in NK["holes"])
SCREWED = [HOLES[0], HOLES[-1]]                      # a diagonal pair
for x, y in HOLES:
    shape = shape.fuse(Part.makeCylinder(SO_R_INSERT if (x, y) in SCREWED else SO_R,
                                         FACE - 0.05 - (PL_BOT - 0.01),
                                         App.Vector(x, y, PL_BOT - 0.01)))
    if (x, y) not in SCREWED:
        shape = shape.fuse(Part.makeCylinder(PIN_D / 2, PIN_LEN + 0.06,
                                             App.Vector(x, y, FACE - 0.06)))
for x, y in NK["key_centres"]:
    shape = shape.cut(box(x - HOLE / 2, x + HOLE / 2, y - HOLE / 2, y + HOLE / 2,
                          PL_TOP - 1, PL_BOT + 1))
for x, y in SCREWED:
    shape = shape.cut(ac.insert_hole((x, y, FACE - 0.05), (0, 0, -1), extra=1.3))
# Front bosses: heat inserts. Back bosses: pegs for the cheek slots.
shape = shape.cut(ac.insert_hole((BX_R, JY_FRONT, JZ), (1, 0, 0)))
shape = shape.cut(ac.insert_hole((BX_L, JY_FRONT, JZ), (-1, 0, 0)))
shape = shape.fuse(Part.makeCylinder(ac.STUB_D / 2, ac.STUB_LEN + 0.01,
                                     App.Vector(BX_R - ac.STUB_LEN, JY_BACK, JZ), X_AXIS))
shape = shape.fuse(Part.makeCylinder(ac.STUB_D / 2, ac.STUB_LEN + 0.01,
                                     App.Vector(BX_L - 0.01, JY_BACK, JZ), X_AXIS))

shape = shape.removeSplitter()
shape.transformShape(ac._matrix("keys"))
shape = ac.save(shape, "deck")
ac.clash(shape)
