# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
"""Write "Cherry MX keycap.wrl": one MX-style switch and an OEM-ish keycap,
for the 3D view only. Adafruit_CAD_Parts has no MX model, so this is blocks
from Cherry's datasheet sizes: bottom housing 14 x 14 below the plate line
(5.0 off the PCB), top housing 15.6 square to 11.6 off the PCB, cross stem to
15.2, keycap 18.2 square at its base. Origin at the switch centre on the PCB's
top surface, +z away from the PCB. VRML units for KiCad are 0.1 in (2.54 mm).

    python3 make_mx_wrl.py
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Cherry MX keycap.wrl")
U = 2.54


def frustum(x0, y0, z0, x1, y1, z1, cx=0.0, cy=0.0):
    """Box-like solid: x0 by y0 at height z0, x1 by y1 at z1, centred on (cx, cy)."""
    pts = []
    for (sx, sy), z in (((x0, y0), z0), ((x1, y1), z1)):
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            pts.append((cx + dx * sx / 2, cy + dy * sy / 2, z))
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return pts, faces


def shape(parts, rgb):
    pts, idx = [], []
    for p, f in parts:
        base = len(pts)
        pts += p
        idx += [", ".join(str(base + i) for i in face) + ", -1" for face in f]
    coords = ", ".join(f"{x / U:.4f} {y / U:.4f} {z / U:.4f}" for x, y, z in pts)
    return (f"Shape {{ appearance Appearance {{ material Material {{ diffuseColor {rgb} "
            f"specularColor 0.2 0.2 0.2 shininess 0.3 }} }}\n"
            f" geometry IndexedFaceSet {{ solid FALSE creaseAngle 0.5 "
            f"coord Coordinate {{ point [ {coords} ] }}\n"
            f" coordIndex [ {', '.join(idx)} ] }} }}\n")


housing = [frustum(14.0, 14.0, 0.0, 14.0, 14.0, 5.0),
           frustum(15.6, 15.6, 5.0, 12.0, 12.0, 11.6)]
stem = [frustum(4.0, 1.3, 11.6, 4.0, 1.3, 15.2),
        frustum(1.1, 4.0, 11.6, 1.1, 4.0, 15.2)]
cap = [frustum(18.2, 18.2, 12.4, 13.0, 13.0, 21.5)]

with open(OUT, "w") as f:
    f.write("#VRML V2.0 utf8\n")
    f.write(shape(housing, "0.12 0.12 0.12"))
    f.write(shape(stem, "0.80 0.10 0.10"))
    f.write(shape(cap, "0.90 0.90 0.88"))
print("wrote", OUT)
