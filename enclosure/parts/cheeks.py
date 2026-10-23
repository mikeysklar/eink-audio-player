# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
"""Cheeks: the two skeletal side frames that give the stand its arcade profile.

The profile is drawn in YZ (u = world y, v = world z) as a union of round joint nodes
and stadium struts, its inside corners filleted by a 2D close (offset out, then in),
clipped flat at the desk, and extruded 4 mm along X. Every layout.json joint gets a
2.8 clear hole and a 4.8 x 1.5 counterbore on the outer face. The left cheek keeps
clear of the USB-C, jack and SW1 keep-out circles and leaves a window for the NeoKey's
STEMMA QT plug; the right cheek is its mirror about X=0.

Print each cheek flat on its outer face (x = -43.5 for L, +43.5 for R), counterbores down
is fine: they are only 1.5 deep and bridge-free circles.
"""

import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import math

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
BAR = 5.0                       # strut width
FILLET = 2.0                    # inside-corner fillet radius

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


faces = [disc(p, NODE_R) for p in J.values()] + [disc(MARQUEE, BAR / 2 + 0.5)]
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

body = prof.extrude(App.Vector(0, 0, T))
for p in J.values():
    body = body.cut(Part.makeCylinder(CLEAR_R, T + 2, App.Vector(p[0], p[1], -1)))
    body = body.cut(Part.makeCylinder(CB_R, CB_D + 1, App.Vector(p[0], p[1], -1)))
body = body.removeSplitter()

# Profile frame (u, v, w) -> world (x = -X_OUT + w, y = u, z = v): w=0 is the outer face.
m = App.Matrix()
(m.A11, m.A21, m.A31), (m.A12, m.A22, m.A32), (m.A13, m.A23, m.A33) = (0, 1, 0), (0, 0, 1), (1, 0, 0)
m.A14 = -X_OUT
cheek_L = body.transformGeometry(m)
cheek_L = Part.Solid(cheek_L.Shells[0]) if len(cheek_L.Solids) == 1 else cheek_L

mir = App.Matrix()
mir.A11 = -1
cheek_R = cheek_L.transformGeometry(mir)

# Keep-outs on the left: ports along X and the NeoKey QT plug window.
print("keep-out mm3 (L):")
pw = L["ports_world"]
for name in ("usb_c", "jack", "sw1_knob"):
    p = pw[name].get("mouth", pw[name].get("centre"))
    cyl = Part.makeCylinder(pw[name]["keepout_d"] / 2, 30, App.Vector(-60, p[1], p[2]),
                            App.Vector(1, 0, 0))
    print("  %-8s %.3f" % (name, cheek_L.common(cyl).Volume))
# The NeoKey's left QT receptacle (its mouth faces -X at x -38.0); the plug has the same
# YZ outline and passes through the cheek. Keep-out = its YZ bbox + 0.3.
qt = [s_ for s_ in ac.bodies()[1].Solids if s_.BoundBox.XMin < -37.5 and s_.Volume < 100
      and s_.BoundBox.YMax < -15 and s_.BoundBox.ZMin < 6][0].BoundBox
qt_yz = (qt.YMin - 0.3, qt.YMax + 0.3, qt.ZMin - 0.3, qt.ZMax + 0.3)
qt_box = Part.makeBox(30, qt_yz[1] - qt_yz[0], qt_yz[3] - qt_yz[2], App.Vector(-60, qt_yz[0], qt_yz[2]))
print("  %-8s %.3f   (y %.2f..%.2f z %.2f..%.2f)" % (("qt_plug", cheek_L.common(qt_box).Volume) + qt_yz))

ac.save(cheek_L, "cheek_L")
ac.clash(cheek_L)
ac.save(cheek_R, "cheek_R")
ac.clash(cheek_R)

# Profile drawing.
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 7))
    for w in prof.Faces[0].Wires:
        pts = w.discretize(Distance=0.5)
        ax.fill([p.x for p in pts], [p.y for p in pts],
                color="#c9b27c" if w.isSame(prof.Faces[0].OuterWire) else "white", zorder=1)
        ax.plot([p.x for p in pts], [p.y for p in pts], color="#555", lw=0.8, zorder=2)
    for k, p in J.items():
        ax.add_patch(plt.Circle(p, CB_R, fill=False, color="k", lw=0.7, zorder=3))
        ax.add_patch(plt.Circle(p, CLEAR_R, color="k", zorder=3))
        ax.annotate(k, p, xytext=(4, 4), textcoords="offset points", fontsize=7)
    for name in ("usb_c", "jack", "sw1_knob"):
        p = pw[name].get("mouth", pw[name].get("centre"))
        ax.add_patch(plt.Circle((p[1], p[2]), pw[name]["keepout_d"] / 2, fill=False,
                                color="red", lw=1, ls="--", zorder=4))
        ax.annotate(name, (p[1], p[2]), color="red", fontsize=7, ha="center")
    ax.add_patch(plt.Rectangle((qt_yz[0], qt_yz[2]), qt_yz[1] - qt_yz[0], qt_yz[3] - qt_yz[2],
                               fill=False, color="blue", ls="--", zorder=4))
    ax.annotate("QT plug", ((qt_yz[0] + qt_yz[1]) / 2, (qt_yz[2] + qt_yz[3]) / 2), color="blue",
                fontsize=7, ha="center")
    ax.axhline(0, color="#888", lw=0.6)
    ax.set_aspect("equal")
    ax.set_xlabel("world y (mm, player at -y)")
    ax.set_ylabel("world z (mm)")
    ax.set_title("left cheek, inner face view (from +x), front at left")
    fig.savefig(ac.BUILD + "/cheek_profile.png", dpi=130, bbox_inches="tight")
    print("wrote build/cheek_profile.png")
except Exception as e:
    print("no profile png:", e)
