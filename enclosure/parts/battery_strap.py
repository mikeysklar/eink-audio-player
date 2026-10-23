# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
# Battery strap: a ladder across the LiPo's lower half, where the display does not cover
# it. Two cross bars hold it against the board, two tabs stop it sliding down the 65 deg
# slope (the gap between them lets the leads out), and the end plates sit on the back of
# the bezel stiles with one M2.5 each, driven from behind into a pilot in the stile.
# Built flat in the board frame and moved to world. Print stile face (z = STILE) down.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import os
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
P = json.load(open(os.path.join(ac.HERE, "inputs", "parts_bbox.json")))
BAT = P["2011 2000mAh Battery"]                      # x 12.03..49.03, y 8.08..68.08
BX_L, BX_R = 30.53 + L["x_in"], 30.53 - L["x_in"]
STILE = -9.35                                        # back face of the bezel stiles
TOP = BAT[4] - 0.1                                   # 0.1 off the battery face
Y0, Y1 = 6.5, 29.0
BARS = ((Y0, Y0 + 5.0), (Y1 - 5.0, Y1))
TABS = ((BAT[0] + 1.0, BAT[0] + 8.0), (BAT[1] - 8.0, BAT[1] - 1.0))
TAB_Z = -0.4                                         # 0.4 short of the board
SCREW_Y = (Y0 + Y1) / 2                              # 17.75, bezel.py pilots here
GAP = 0.3


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


shape = box(BX_R, BX_R + 6.0, Y0, Y1, STILE, TOP)
shape = shape.fuse(box(BX_L - 6.0, BX_L, Y0, Y1, STILE, TOP))
for y0, y1 in BARS:
    shape = shape.fuse(box(BX_R, BX_L, y0, y1, STILE, TOP))
for x0, x1 in TABS:
    shape = shape.fuse(box(x0, x1, Y0, BAT[2] - GAP, STILE, TAB_Z))
for x in (BX_R + 3.0, BX_L - 3.0):
    shape = shape.cut(Part.makeCylinder(1.4, 5, App.Vector(x, SCREW_Y, STILE - 1)))

shape = shape.removeSplitter()
shape.transformShape(ac._matrix("stack"))
shape = ac.save(shape, "battery_strap")
ac.clash(shape)
