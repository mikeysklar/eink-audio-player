# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Put the stand together and check it.

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd assemble_arcade.py

Reads every part STEP in build/ (written by parts/*.py), checks each one against the
placed board models and against every other part, then writes build/arcade.FCStd (parts,
stack and keys as separate coloured objects, for looking at) and build/arcade.step.
"""

import os
import sys

sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.dirname(os.path.abspath(__file__)))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

import arcade_common as ac  # noqa: E402

PARTS = ["bezel", "deck", "cheek_L", "cheek_R", "brace_front", "brace_rear", "brace_top",
         "battery_strap", "ano_mount"]
COLORS = {"bezel": (0.10, 0.10, 0.12), "deck": (0.10, 0.10, 0.12),
          "cheek_L": (0.85, 0.20, 0.30), "cheek_R": (0.85, 0.20, 0.30),
          "brace_front": (0.10, 0.10, 0.12), "brace_rear": (0.10, 0.10, 0.12),
          "brace_top": (0.85, 0.20, 0.30), "battery_strap": (0.10, 0.10, 0.12),
          "ano_mount": (0.10, 0.10, 0.12)}

shapes = {}
for name in PARTS:
    path = os.path.join(ac.BUILD, name + ".step")
    if not os.path.exists(path):
        print("MISSING", name)
        continue
    shapes[name] = Part.read(path)

stack, keys = ac.bodies()
ano = Part.read(os.path.join(ac.BUILD, "ano.step"))     # placed by parts/ano_mount.py
fails = 0
for name, s in shapes.items():
    c = ac.clash(s, verbose=False)
    ok = s.isValid() and len(s.Solids) == 1 and c["stack"] < 0.01 and c["keys"] < 0.01
    fails += not ok
    print("%-4s %-12s valid=%s solids=%d clash stack=%.3f keys=%.3f vol=%.0f" % (
        "PASS" if ok else "FAIL", name, s.isValid(), len(s.Solids), c["stack"], c["keys"],
        s.Volume))

names = list(shapes)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if not shapes[a].BoundBox.intersect(shapes[b].BoundBox):
            continue
        v = shapes[a].common(shapes[b]).Volume
        if v > 0.01:
            fails += 1
            print("FAIL overlap %s / %s: %.3f mm3" % (a, b, v))

for name, s in shapes.items():
    v = sum(a.common(s).Volume for a in ano.Solids if a.BoundBox.intersect(s.BoundBox))
    fails += v > 0.01
    if v > 0.01:
        print("FAIL overlap ano / %s: %.3f mm3" % (name, v))

# Joints: each should have material from its owner and a cheek around the screw axis.
L = ac.layout()
for j, p in L["joints"].items():
    side = j[-1]
    cheek = shapes.get("cheek_" + side)
    owner = {"bezel": "bezel", "deck": "deck", "foot": None, "top": "brace_top"}[j.split("_")[0]]
    if j.startswith("foot_front"):
        owner = "brace_front"
    elif j.startswith("foot_rear"):
        owner = "brace_rear"
    sx = -1 if side == "L" else 1
    # A ring round the pilot (r 1.1), 1 to 5 mm in from the cheek face.
    a = App.Vector(p[0] - sx * 5.0, p[1], p[2])
    probe_in = (Part.makeCylinder(2.5, 4.0, a, App.Vector(sx, 0, 0))
                .cut(Part.makeCylinder(1.4, 4.0, a, App.Vector(sx, 0, 0))))
    probe_ch = Part.makeCylinder(2.2, 4.0, App.Vector(p[0], p[1], p[2]), App.Vector(sx, 0, 0))
    got_o = shapes[owner].common(probe_in).Volume if owner in shapes else 0
    got_c = cheek.common(probe_ch).Volume if cheek else 0
    ok = got_o > 0.5 and got_c > 1.0
    fails += not ok
    print("%-4s joint %-15s owner %-11s %.1f mm3  cheek %.1f mm3" % (
        "PASS" if ok else "FAIL", j, owner, got_o, got_c))

doc = App.newDocument("arcade")
for name, s in shapes.items():
    o = doc.addObject("Part::Feature", name)
    o.Shape = s
st = doc.addObject("Part::Feature", "board_stack")
st.Shape = stack
ky = doc.addObject("Part::Feature", "neokey_keys")
ky.Shape = keys
an = doc.addObject("Part::Feature", "ano")
an.Shape = ano
fc = os.path.join(ac.BUILD, "arcade.FCStd")
doc.saveAs(fc)
Part.makeCompound(list(shapes.values())).exportStep(os.path.join(ac.BUILD, "arcade.step"))

# Colours go straight into GuiDocument.xml (no ViewObject headless).
import zipfile  # noqa: E402
import re  # noqa: E402
cols = dict(COLORS, board_stack=(0.05, 0.35, 0.20), neokey_keys=(0.90, 0.90, 0.88),
            ano=(0.08, 0.08, 0.08))
zin = zipfile.ZipFile(fc)
items = {n: zin.read(n) for n in zin.namelist()}
zin.close()
gui = ('<?xml version="1.0" encoding="utf-8"?>\n<Document SchemaVersion="1">\n'
       '<ViewProviderData Count="%d">\n' % len(cols))
for n, (r, g, b) in cols.items():
    packed = (int(r * 255) << 24) | (int(g * 255) << 16) | (int(b * 255) << 8)
    gui += ('<ViewProvider name="%s" expanded="0"><Properties Count="2">'
            '<Property name="ShapeColor" type="App::PropertyColor"><PropertyColor value="%d"/></Property>'
            '<Property name="Visibility" type="App::PropertyBool"><Bool value="true"/></Property>'
            '</Properties></ViewProvider>\n' % (n, packed))
gui += "</ViewProviderData>\n<Camera settings=\"\"/>\n</Document>\n"
items["GuiDocument.xml"] = gui.encode()
zout = zipfile.ZipFile(fc, "w", zipfile.ZIP_DEFLATED)
for n, d in items.items():
    zout.writestr(n, d)
zout.close()
print("wrote", fc)
print("%d fail(s)" % fails)
