# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Stack cradle: one printed part between the board and the display, in place of the four
# brass standoffs and the battery strap. Four posts span the 9.5 mm from the display PCB's
# back to the board at H1-H4; four M2.5 x 16 screws from the board side run through the
# board, the posts and the display into heat inserts in the bezel, and clamp it all. Side
# rails tie each pair of posts and run down past the display to two bars across the
# LiPo's lower half, with two tabs that stop the LiPo sliding down the slope (the gap
# between them lets the leads out).
# Built flat in the board frame and moved to world. Print display face (z = Z_BED) down.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import os
import FreeCAD as App
import Part
import arcade_common as ac

D = json.load(open(os.path.join(ac.HERE, "inputs", "measure_display.json")))
P = json.load(open(os.path.join(ac.HERE, "inputs", "parts_bbox.json")))
BAT = P["2011 2000mAh Battery"]                      # x 12.03..49.03, y 8.08..68.08
Z_BED = D["pcb"]["bbox"][5]                          # display PCB back, -9.515
POST_R, CLEAR_D = 3.0, 2.8
RAIL_W, RAIL_TOP = 4.0, -5.0                         # rails stand off the board's back by 5
BAR_TOP = BAT[4] - 0.1                               # 0.1 off the LiPo face
Y0, Y1 = 6.5, 29.0
BARS = ((Y0, Y0 + 5.0), (Y1 - 5.0, Y1))
TABS = ((BAT[0] + 1.0, BAT[0] + 8.0), (BAT[1] - 8.0, BAT[1] - 1.0))
TAB_Z = -0.4                                         # 0.4 short of the board
GAP = 0.3
HOLES = D["pcb"]["holes"]                            # (2.59|58.47, 39.28|73.57)
XS = sorted({h[0] for h in HOLES})
YS = sorted({h[1] for h in HOLES})


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


parts = []
for hx, hy in HOLES:
    parts.append(Part.makeCylinder(POST_R, -Z_BED, App.Vector(hx, hy, Z_BED)))
for x in XS:
    parts.append(box(x - RAIL_W / 2, x + RAIL_W / 2, Y0, YS[1], Z_BED, RAIL_TOP))
for y0, y1 in BARS:
    parts.append(box(XS[0], XS[1], y0, y1, Z_BED, BAR_TOP))
for x0, x1 in TABS:
    parts.append(box(x0, x1, Y0, BAT[2] - GAP, Z_BED, TAB_Z))
shape = parts[0].fuse(parts[1:])
# Parts on the display's back (its FPC connector on the right, a 1.9 mm part on the left)
# sit over the rails: lift the rails over each one's box plus GAP.
inv = ac._matrix("stack").inverse()
for sol in ac.bodies()[0].Solids:
    c = sol.copy()
    c.transformShape(inv)
    b = c.BoundBox
    if b.ZMax > Z_BED + 0.01 and b.ZMin < Z_BED + 0.01 and b.ZMax < RAIL_TOP - 1.5 and \
            any(b.XMin < x + RAIL_W / 2 and b.XMax > x - RAIL_W / 2 for x in XS) and \
            b.YMax > Y0 and b.YMin < YS[1]:
        print("lift rail over", [round(t, 2) for t in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMax)])
        shape = shape.cut(box(b.XMin - GAP, b.XMax + GAP, b.YMin - GAP, b.YMax + GAP, Z_BED - 1,
                              b.ZMax + GAP))
for hx, hy in HOLES:
    shape = shape.cut(Part.makeCylinder(CLEAR_D / 2, 20, App.Vector(hx, hy, Z_BED - 5)))

shape = shape.removeSplitter()
shape.transformShape(ac._matrix("stack"))
shape = ac.save(shape, "cradle")
ac.clash(shape)
