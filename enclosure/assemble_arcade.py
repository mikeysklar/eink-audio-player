# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Put the stand together and check it.

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd assemble_arcade.py

Reads every part STEP in build/ (written by parts/*.py), checks each one against the
placed board models and against every other part, checks the hardware (fasteners.py)
against everything, sweeps each part along the way it goes in, then writes
build/arcade.FCStd (parts, stack, keys and hardware as separate coloured objects, for
looking at) and build/arcade.step.
"""

import math
import os
import sys

sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.dirname(os.path.abspath(__file__)))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

import arcade_common as ac  # noqa: E402

PARTS = ["chassis", "bezel", "deck", "cradle", "handle"]
COLORS = {"chassis": (0.85, 0.20, 0.30), "bezel": (0.10, 0.10, 0.12),
          "deck": (0.10, 0.10, 0.12), "cradle": (0.10, 0.10, 0.12),
          "handle": (0.85, 0.20, 0.30)}

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

# Hardware: heads, and shanks and inserts at their holes' cores, touch nothing.
hw = Part.Shape()
hw.read(os.path.join(ac.BUILD, "fasteners_check.brep"))
for i, f in enumerate(hw.Solids):
    bad = [(n, v) for n, v in ((n, f.common(sh).Volume) for n, sh in shapes.items()
                               if f.BoundBox.intersect(sh.BoundBox)) if v > 0.01]
    c = ac.clash(f, verbose=False)
    bad += [(n, v) for n, v in c.items() if v > 0.01]
    bad += [("ano", v) for v in [sum(a.common(f).Volume for a in ano.Solids
                                     if a.BoundBox.intersect(f.BoundBox))] if v > 0.01]
    fails += bool(bad)
    if bad:
        print("FAIL hardware %d: %s" % (i, ", ".join("%s %.3f mm3" % b for b in bad)))
print("hardware: %d items checked" % len(hw.Solids))

# Each part's way in, run backwards: no overlap with what is already in place.
L = ac.layout()


def sweep(label, moving, fixed, d, run, step=2.0):
    worst = 0.0
    for k in range(1, int(run / step) + 1):
        off = App.Vector(*d) * (k * step)
        for m in moving:
            mm = m.copy()
            mm.translate(off)
            for f in fixed:
                if mm.BoundBox.intersect(f.BoundBox):
                    worst = max(worst, mm.common(f).Volume)
    ok = worst < 0.01
    print("%-4s sweep %-34s worst %.3f mm3" % ("PASS" if ok else "FAIL", label, worst))
    return not ok


near = lambda body, box: [x for x in body.Solids if x.BoundBox.intersect(box)]
n = App.Vector(*L["stack"]["normal_to_player"])
feet = App.BoundBox(-40, -80, -1, 90, 80, 10.5)
fails += sweep("bezel+cradle+stack, out to the front", [shapes["bezel"], shapes["cradle"]] +
               near(stack, feet), [shapes["chassis"]], n, 70)
keys_only = [x for x in keys.Solids if x.BoundBox.XMax < 41]
fails += sweep("deck+keys, up", [shapes["deck"]] + keys_only,
               [shapes["chassis"], shapes["bezel"]], (0, 0, 1), 50)
# The handle's snap barb squeezes through its 4.0 hole by design: sweep it without the pin.
bar = shapes["handle"].common(Part.makeBox(150 + L["x_in"], 200, 200, App.Vector(-150, -100, -100)))
fails += sweep("handle (less its snap pin), out to the left", [bar],
               [shapes["chassis"], shapes["bezel"]] + near(stack, shapes["handle"].BoundBox),
               (-1, 0, 0), 90, step=3.0)
fails += sweep("ANO, up off its standoffs", ano.Solids, [shapes["chassis"]],
               tuple(-v for v in (0, math.sin(math.radians(L["deck_deg"])),
                                  -math.cos(math.radians(L["deck_deg"])))), 12)

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
hw_o = doc.addObject("Part::Feature", "hardware")
hw_o.Shape = Part.read(os.path.join(ac.BUILD, "fasteners.step"))
fc = os.path.join(ac.BUILD, "arcade.FCStd")
doc.saveAs(fc)
Part.makeCompound(list(shapes.values())).exportStep(os.path.join(ac.BUILD, "arcade.step"))

# Colours go straight into GuiDocument.xml (no ViewObject headless).
import zipfile  # noqa: E402
import re  # noqa: E402
cols = dict(COLORS, board_stack=(0.05, 0.35, 0.20), neokey_keys=(0.90, 0.90, 0.88),
            ano=(0.08, 0.08, 0.08), hardware=(0.75, 0.75, 0.78))
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
