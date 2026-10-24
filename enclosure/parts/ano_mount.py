# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# ANO mount: holds the Adafruit ANO rotary encoder (6310, model from Adafruit_CAD_Parts
# "5740 ANO Rotary Encoder QT") past the right end of the keys and toward the player, for
# the thumb, tilted DECK_DEG like the keys. It is fused into the chassis (chassis.py): an
# arm on the right cheek's outer face, with an open bore over the deck_front_R screw head,
# a frame under the ANO with four standoffs (two take heat inserts for M2.5 x 6 screws
# from the ANO's top, two have pins through its holes), and the frame's front rail runs
# down to the desk so a thumb press does not lever the stand.
# The ANO's STEMMA QT on its back edge faces the stand: the cable runs from the NeoKey's
# right port, through the cheek window, to it.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import math
import os
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
ANO_STEP = os.path.join(ac.HERE, "..", "kicad", "3d", "5740 ANO Rotary Encoder QT.step")
X_OUT = L["x_in"] + L["cheek_t"]                    # right cheek outer face, 43.5
T = 4.0                                              # arm thickness, x 43.5..47.5
HEAD_BORE = 5.4                                     # socket head 4.5 + room for a hex key
NODE_R, BAR = L["screw"]["clear_d"] / 2 + 3.5, 5.0   # as the cheeks

# ANO frame (its STEP: board z 0..1.57, wheel on -z, holes at (+-15.24, +-17.78)).
# u (STEP x) runs up the slope toward the stand, v (STEP y) to the player's right, w (STEP
# z) down into the mount, so the wheel faces up.
DEG = math.radians(L["deck_deg"])
EX = App.Vector(0, math.cos(DEG), math.sin(DEG))
EY = App.Vector(1, 0, 0)
EZ = App.Vector(0, math.sin(DEG), -math.cos(DEG))
HU, HV = 17.78, 20.32                               # board half sizes
CENTRE = App.Vector(X_OUT + HV, -54.0, 14.07)       # left edge on the cheek face
HOLES = [(su * 15.24, sv * 17.78) for su in (-1, 1) for sv in (-1, 1)]
BOARD_BACK = 1.57
SO_TOP, PL_TOP, PL_BOT = BOARD_BACK + 0.05, BOARD_BACK + 3.6, BOARD_BACK + 6.1
RAIL = 5.0


def ano_matrix():
    m = App.Matrix()
    (m.A11, m.A21, m.A31), (m.A12, m.A22, m.A32), (m.A13, m.A23, m.A33) = EX, EY, EZ
    m.A14, m.A24, m.A34 = CENTRE
    return m


def uvw(u, v, w):
    return CENTRE + EX * u + EY * v + EZ * w


def rounded(hu, hv, r, w0, w1):
    b = Part.makeBox(2 * hu, 2 * hv, w1 - w0, App.Vector(-hu, -hv, w0))
    if r > 0:
        b = b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Point.x
                             - e.Vertexes[1].Point.x) < 1e-6 and abs(e.Vertexes[0].Point.y
                             - e.Vertexes[1].Point.y) < 1e-6])
    return b


# Frame and standoffs, ANO frame.
frame = rounded(HU, HV, 2.54, PL_TOP, PL_BOT).cut(
    Part.makeBox(2 * (HU - RAIL), 2 * (HV - RAIL), 10, App.Vector(-(HU - RAIL), -(HV - RAIL), 0)))
SCREWED = [HOLES[0], HOLES[-1]]                     # a diagonal pair
for u, v in HOLES:
    frame = frame.fuse(Part.makeCylinder(3.0, PL_TOP - SO_TOP + 0.01, App.Vector(u, v, SO_TOP)))
    if (u, v) not in SCREWED:                       # pin into the ANO's 2.5 hole
        frame = frame.fuse(Part.makeCylinder(1.1, 1.41, App.Vector(u, v, SO_TOP - 1.4)))
# Front rail down to the desk: a deep bar under it, cut flat at z = 0 once in world.
frame = frame.fuse(Part.makeBox(RAIL, 2 * HV - 5.08, 30, App.Vector(-HU, -HV + 2.54, PL_TOP)))
for u, v in SCREWED:
    frame = frame.cut(ac.insert_hole((u, v, SO_TOP), (0, 0, 1), extra=1.5))
frame.transformShape(ano_matrix())
frame = frame.common(Part.makeBox(200, 200, 100, App.Vector(-20, -150, 0)))

# Arm on the cheek's outer face, profile in world (y, z), extruded along +x.
jb, jf = L["joints"]["deck_back_R"], L["joints"]["deck_front_R"]
rear = uvw(HU - RAIL / 2, -HV + RAIL / 2, (PL_TOP + PL_BOT) / 2)   # rear-left of the frame


def disc(y, z, r):
    return Part.makeCylinder(r, T, App.Vector(X_OUT, y, z), App.Vector(1, 0, 0))


def strut(a, b, w):
    dy, dz = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dy, dz)
    ny, nz = -dz / n * w / 2, dy / n * w / 2
    pts = [(a[0] + ny, a[1] + nz), (b[0] + ny, b[1] + nz), (b[0] - ny, b[1] - nz),
           (a[0] - ny, a[1] - nz)]
    f = Part.Face(Part.makePolygon([App.Vector(X_OUT, y, z) for y, z in pts + pts[:1]]))
    return f.extrude(App.Vector(T, 0, 0)).fuse([disc(a[0], a[1], w / 2), disc(b[0], b[1], w / 2)])


arm = disc(jb[1], jb[2], NODE_R).fuse([
    disc(jf[1], jf[2], NODE_R),
    strut((jb[1], jb[2]), (jf[1], jf[2]), BAR),
    strut((jf[1], jf[2]), (rear.y, rear.z), BAR),
])
# The deck_front_R screw head sits in the cheek's counterbore; the arm leaves it open.
arm = arm.cut(Part.makeCylinder(HEAD_BORE / 2, T + 2, App.Vector(X_OUT - 1, jf[1], jf[2]),
                                App.Vector(1, 0, 0)))

shape = frame.fuse(arm).removeSplitter()
shape = ac.save(shape, "ano_mount")
ac.clash(shape)

# The placed ANO model, for the assembly and the renders.
ano = Part.read(ANO_STEP)
ano.transformShape(ano_matrix())
ano.exportStep(os.path.join(ac.BUILD, "ano.step"))
ano.exportBrep(os.path.join(ac.BUILD, "ano.brep"))
b = ano.BoundBox
print("ano placed bbox", [round(x, 2) for x in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)])
print("ano / mount mm3: %.3f" % sum(s.common(shape).Volume for s in ano.Solids
                                     if s.BoundBox.intersect(shape.BoundBox)))
print("ano / stack mm3: %.3f" % ac.clash(ano, verbose=False)["stack"])
# The keys body also carries board.step's ANO1 (build_pcb.py): its box should match this one.
k = Part.makeCompound([x for x in ac.bodies()[1].Solids if x.BoundBox.XMin > 40.0]).BoundBox
print("ano bbox vs its KiCad copy: max diff %.3f mm" % max(abs(u - v) for u, v in zip(
    (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax), (k.XMin, k.XMax, k.YMin, k.YMax, k.ZMin, k.ZMax))))
w = uvw(0, 0, -5.8)
print("wheel top centre (world): %.1f %.1f %.1f" % (w.x, w.y, w.z))
# The NeoKey's right QT plug window through the cheek (mirror of cheeks.py's left one).
qt = [s_ for s_ in ac.bodies()[1].Solids if s_.BoundBox.XMax > 37.5 and s_.Volume < 100
      and s_.BoundBox.YMax < -15 and s_.BoundBox.ZMin < 6][0].BoundBox
qt_box = Part.makeBox(30, qt.YLength + 0.6, qt.ZLength + 0.6,
                      App.Vector(30, qt.YMin - 0.3, qt.ZMin - 0.3))
print("qt plug window / mount mm3: %.3f" % shape.common(qt_box).Volume)
