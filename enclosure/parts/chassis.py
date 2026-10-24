# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Chassis: the two cheeks, the front and rear foot bars and the ANO mount, as one print.

The cheek profile is drawn in YZ (u = world y, v = world z) as a union of round joint nodes
and stadium struts, its inside corners filleted by a 2D close (offset out, then in),
clipped flat at the desk, and extruded 4 mm along X; the right cheek is the left one's
mirror about X=0. The left cheek keeps clear of the USB-C, jack and SW1 keep-out circles,
and both leave a window for the NeoKey's STEMMA QT plugs.

What the other parts meet, on each cheek:
  bezel_top, deck_front  2.8 clear hole, 4.8 x 1.5 counterbore outside: one M2.5 x 8 into
                         the part's heat insert.
  bezel_bottom           a slot on the inner face, open toward the player: the bezel's peg
                         slides in as the bezel goes in from the front.
  deck_back              a slot on the inner face, open straight up: the deck's peg drops in.
  top_rear               the handle: 7.4 through on the left for the rod, 4.0 on the right
                         for its snap.

Print upright on the feet, with tree supports under the struts, the deck rail and the ANO
frame.
"""

import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import math
import os

import FreeCAD as App
import Part

import arcade_common as ac

L = ac.layout()
X_IN = L["x_in"]
T = L["cheek_t"]
X_OUT = X_IN + T
CLEAR_R = L["screw"]["clear_d"] / 2
CB_R, CB_D = 4.8 / 2, 1.5
NODE_R = CLEAR_R + 3.5          # 3.5 of material round the hole (more and deck_front hits the QT plug)
HANDLE_NODE_R = 6.8             # round the 7.4 handle hole
HANDLE_D, SNAP_D = 7.4, 4.0
BAR = 5.0                       # strut width
FILLET = 2.0                    # inside-corner fillet radius
FOOT_W, FOOT_H = 6.0, 10.0      # foot bars, on the desk from Z=0

J = {k[:-2]: (v[1], v[2]) for k, v in L["joints"].items() if k.endswith("_L")}

# Extra profile points (y, z), not joints.
MARQUEE = (25.0, 88.0)          # hood tip, proud of the screen line like an arcade marquee
BASE_Z = 2.25                   # base rail centre: z 0..4.75 once clipped, under the QT plug
D = (-2.0, BASE_Z)               # where the deck-to-screen triangle lands on the base rail
WAIST_Z = 30.3                  # waist rail threads between the jack and the USB-C / SW1


def _on_line(a, b, z):
    t = (z - a[1]) / (b[1] - a[1])
    return (a[0] + t * (b[0] - a[0]), z)


WAIST_F = _on_line(J["bezel_bottom"], J["bezel_top"], WAIST_Z)
WAIST_R = _on_line(J["foot_rear"], J["top_rear"], WAIST_Z)

STRUTS = [
    ((J["foot_front"][0], BASE_Z), (J["foot_rear"][0], BASE_Z)),   # base rail, also the foot
    (J["foot_front"], J["deck_front"]),      # front leg
    (J["deck_front"], J["deck_back"]),       # deck rail
    (J["deck_back"], J["bezel_bottom"]),     # deck to screen
    (J["deck_back"], D),                     # triangle down to the base
    (J["bezel_bottom"], D),
    (J["bezel_bottom"], J["bezel_top"]),     # screen rail, 65 deg
    (J["bezel_top"], MARQUEE),               # marquee lip
    (MARQUEE, J["top_rear"]),                # hood / roof
    (J["top_rear"], J["foot_rear"]),         # back leg
    (WAIST_F, WAIST_R),                      # waist rail
    (J["bezel_bottom"], J["foot_rear"]),     # lower diagonal, under the jack
]


def _v(p):
    return App.Vector(p[0], p[1], 0)


def disc(p, r):
    return Part.Face(Part.Wire(Part.makeCircle(r, _v(p))))


def stadium(a, b, w):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n * w / 2, dx / n * w / 2
    pts = [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
           (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]
    box = Part.Face(Part.makePolygon([_v(p) for p in pts + pts[:1]]))
    return box.fuse([disc(a, w / 2), disc(b, w / 2)])


faces = [disc(p, HANDLE_NODE_R if k == "top_rear" else NODE_R) for k, p in J.items()]
faces += [disc(MARQUEE, BAR / 2 + 0.5)]
faces += [stadium(a, b, BAR) for a, b in STRUTS]
# 2D fuses leave split faces; fuse thin slabs instead and keep the merged bottom face.
slab = Part.makeCompound([f.extrude(App.Vector(0, 0, 1)) for f in faces])
slab = slab.Solids[0].multiFuse(slab.Solids[1:]).removeSplitter()
prof = [f for f in slab.Faces if abs(f.BoundBox.ZMax) < 1e-6][0]
# Close: grow then shrink, which fillets the inside corners where struts meet.
prof = prof.makeOffset2D(FILLET, join=0).makeOffset2D(-FILLET, join=0)
# Clip flat at the desk.
prof = prof.common(Part.Face(Part.makePolygon([_v(p) for p in
                                               [(-80, 0), (120, 0), (120, 150), (-80, 150), (-80, 0)]])))


body = prof.extrude(App.Vector(0, 0, T)).removeSplitter()

# Profile frame (u, v, w) -> world (x = -X_OUT + w, y = u, z = v): w=0 is the outer face.
m = App.Matrix()
(m.A11, m.A21, m.A31), (m.A12, m.A22, m.A32), (m.A13, m.A23, m.A33) = (0, 1, 0), (0, 0, 1), (1, 0, 0)
m.A14 = -X_OUT
cheek_L = body.transformGeometry(m)
mir = App.Matrix()
mir.A11 = -1
cheek_R = cheek_L.transformGeometry(mir)

feet = [Part.makeBox(2 * X_IN + 1.0, FOOT_W, FOOT_H,
                     App.Vector(-X_IN - 0.5, L["joints"]["foot_" + k + "_L"][1] - FOOT_W / 2, 0))
        for k in ("front", "rear")]
ano_mount = Part.read(os.path.join(ac.BUILD, "ano_mount.step"))
shape = cheek_L.fuse([cheek_R] + feet + [ano_mount])

X_AXIS = App.Vector(1, 0, 0)
N = L["stack"]["normal_to_player"]          # the bezel's way in, reversed


def slot(p, d, sx):
    """Slot on a cheek's inner face at joint p, open along (dy, dz) = d, SLOT_DEPTH deep."""
    x0 = sx * X_IN - (sx > 0) * 0.01 + (sx < 0) * 0.01
    a = App.Vector(x0 if sx > 0 else x0 - ac.SLOT_DEPTH, 0, 0)
    n = math.hypot(*d)
    dy, dz = d[0] / n, d[1] / n
    r = ac.SLOT_W / 2
    run = 20.0                               # well past the cheek's edge
    pts = [(p[1] - dz * r, p[2] + dy * r), (p[1] - dz * r + dy * run, p[2] + dy * r + dz * run),
           (p[1] + dz * r + dy * run, p[2] - dy * r + dz * run), (p[1] + dz * r, p[2] - dy * r)]
    f = Part.Face(Part.makePolygon([App.Vector(a.x, y, z) for y, z in pts + pts[:1]]))
    return f.extrude(App.Vector(ac.SLOT_DEPTH + 0.01, 0, 0)).fuse(
        Part.makeCylinder(r, ac.SLOT_DEPTH + 0.01, App.Vector(a.x, p[1], p[2]), X_AXIS))


for side, sx in (("L", -1), ("R", 1)):
    J3 = {k: L["joints"][k + "_" + side] for k in ("bezel_top", "bezel_bottom", "deck_back",
                                                   "deck_front", "top_rear")}
    for k in ("bezel_top", "deck_front"):
        p = App.Vector(*J3[k])
        shape = shape.cut(Part.makeCylinder(CLEAR_R, T + 2, App.Vector(sx * (X_IN - 1), p.y, p.z),
                                            App.Vector(sx, 0, 0)))
        shape = shape.cut(Part.makeCylinder(CB_R, CB_D + 1, App.Vector(sx * (X_OUT - CB_D), p.y, p.z),
                                            App.Vector(sx, 0, 0)))
    shape = shape.cut(slot(J3["bezel_bottom"], (N[1], N[2]), sx))
    shape = shape.cut(slot(J3["deck_back"], (0.0, 1.0), sx))
    p = J3["top_rear"]
    shape = shape.cut(Part.makeCylinder((HANDLE_D if sx < 0 else SNAP_D) / 2, T + 2,
                                        App.Vector(sx * (X_IN - 1), p[1], p[2]), App.Vector(sx, 0, 0)))

# Keep-outs on the left: ports along X and the NeoKey QT plug windows.
print("keep-out mm3 (L):")
pw = L["ports_world"]
for name in ("usb_c", "jack", "sw1_knob"):
    p = pw[name].get("mouth", pw[name].get("centre"))
    cyl = Part.makeCylinder(pw[name]["keepout_d"] / 2, 30, App.Vector(-60, p[1], p[2]), X_AXIS)
    print("  %-8s %.3f" % (name, shape.common(cyl).Volume))
for sx in (-1, 1):
    qt = [s_ for s_ in ac.bodies()[1].Solids if s_.Volume < 100 and s_.BoundBox.YMax < -15
          and s_.BoundBox.ZMin < 6 and (s_.BoundBox.XMin < -37.5 if sx < 0 else s_.BoundBox.XMax > 37.5)][0].BoundBox
    qt_box = Part.makeBox(30, qt.YLength + 0.6, qt.ZLength + 0.6,
                          App.Vector(-60 if sx < 0 else 30, qt.YMin - 0.3, qt.ZMin - 0.3))
    print("  qt plug %s %.3f" % ("L" if sx < 0 else "R", shape.common(qt_box).Volume))

shape = ac.save(shape.removeSplitter(), "chassis")
ac.clash(shape)
