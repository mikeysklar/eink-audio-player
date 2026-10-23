# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Cross braces tying the cheeks together: front and rear foot bars on the desk, and a
# round top bar that doubles as a carry handle. Built in world mm, desk Z=0.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
X_IN = L["x_in"]                       # cheek inner faces, +-39.5
J = L["joints"]
PILOT_D = 2.2
PILOT_DEPTH = 6.0
FOOT_W = 6.0                           # bar Y width
FOOT_H = 10.0                          # bar Z height, on the desk from Z=0
TOP_D = 7.0
X_AXIS = App.Vector(1, 0, 0)


def pilot(shape, p):
    # Hole from the end face inward 6 mm, centred on the joint point. Starts 1 mm past
    # the face on the outside so the cut is clean.
    x, y, z = p
    if x > 0:
        x0 = x - PILOT_DEPTH
    else:
        x0 = x - 1.0
    cut = Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH + 1.0, App.Vector(x0, y, z), X_AXIS)
    return shape.cut(cut)


def near_dist(shape, body, reach=15.0):
    # Min distance to the body's solids whose bbox is within reach of the part (the full
    # stack compound is too slow to measure against whole).
    near = App.BoundBox(shape.BoundBox)
    near.enlarge(reach)
    best = None
    for sol in body.Solids:
        if not sol.BoundBox.intersect(near):
            continue
        d = shape.distToShape(sol)[0]
        best = d if best is None else min(best, d)
    return round(best, 3) if best is not None else ">%g" % reach


def report(name, shape):
    ac.save(shape, name)
    ac.clash(shape)
    stack, keys = ac.bodies()
    print(name, "dist to stack:", near_dist(shape, stack), "dist to keys:", near_dist(shape, keys))


def foot_bar(name, jl, jr):
    y = jl[1]
    bar = Part.makeBox(2 * X_IN, FOOT_W, FOOT_H, App.Vector(-X_IN, y - FOOT_W / 2, 0))
    bar = pilot(bar, jl)
    bar = pilot(bar, jr)
    report(name, bar)


foot_bar("brace_front", J["foot_front_L"], J["foot_front_R"])
foot_bar("brace_rear", J["foot_rear_L"], J["foot_rear_R"])

tl, tr = J["top_rear_L"], J["top_rear_R"]
top = Part.makeCylinder(TOP_D / 2, 2 * X_IN, App.Vector(-X_IN, tl[1], tl[2]), X_AXIS)
top = pilot(top, tl)
top = pilot(top, tr)
report("brace_top", top)
