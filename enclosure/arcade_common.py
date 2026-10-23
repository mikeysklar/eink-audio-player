# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
"""FreeCAD helpers shared by every part script. Import from a freecadcmd script:

    import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.dirname(os.path.abspath(__file__)))
    import arcade_common as ac
    L = ac.layout()                       # layout.json as a dict
    stack, keys = ac.bodies()             # placed board models, world frame (cached BREPs)
    v = ac.stack_pt((x, y, z))            # board-frame point -> world FreeCAD Vector
    v = ac.keys_pt((x, y, z))             # NeoKey (board frame) point -> world Vector
    ac.save(shape, "bezel")               # writes build/bezel.step + .stl, prints volume/solids
    ac.clash(shape)                       # mm3 of shape inside stack / keys, prints both

`keys` includes the NeoKey from the STEP plus four MX switch + keycap envelopes
(boxes from 3d/make_mx_wrl.py: housing 15.6 sq to 11.6, keycap 18.2 sq from 12.4 to
21.5 above the NeoKey face). Run this file itself once to (re)build the cache:

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd arcade_common.py
"""

import json
import os
import sys

import FreeCAD as App
import Part

HERE = os.environ.get("EAP_ROOT") or os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
STEP = os.path.join(HERE, "inputs", "board.step")


def layout():
    return json.load(open(os.path.join(HERE, "layout.json")))


def _matrix(body):
    b = layout()[body]
    m = App.Matrix()
    (m.A11, m.A21, m.A31), (m.A12, m.A22, m.A32), (m.A13, m.A23, m.A33) = b["bx"], b["by"], b["bz"]
    m.A14, m.A24, m.A34 = b["p0"]
    return m


def stack_pt(p):
    return _matrix("stack").multVec(App.Vector(*p))


def keys_pt(p):
    return _matrix("keys").multVec(App.Vector(*p))


def _build_cache():
    import Import
    doc = App.newDocument("src")
    Import.insert(STEP, doc.Name)
    stack, neokey = [], []
    for o in doc.Objects:
        if o.TypeId == "App::Part" and o.InList and all(not q.InList for q in o.InList):
            if o.Shape.isNull():
                continue
            (neokey if o.Label.startswith("4980") else stack).append(o.Shape.copy())
    for o in doc.Objects:
        if (o.TypeId == "Part::Feature" and o.InList and all(not q.InList for q in o.InList)
                and not o.Shape.isNull()):
            stack.append(o.Shape.copy())     # the PCB itself, tracks, pads, silk
    s = Part.makeCompound(stack)
    s.transformShape(_matrix("stack"))
    k = Part.makeCompound(neokey)
    face = -12.115
    mx = []
    for x, y in json.load(open(os.path.join(
            HERE, "inputs", "measure_neokey_sw1.json")))["neokey"]["key_centres"]:
        # Keys stand on the -Z side of the NeoKey (its face is at z=face). Below the plate
        # (face to face-5.0) the housing is the 14.0 snap-in body; above it the 15.6 top.
        mx.append(Part.makeBox(14.0, 14.0, 5.0, App.Vector(x - 7.0, y - 7.0, face - 5.0)))
        mx.append(Part.makeBox(15.6, 15.6, 6.6, App.Vector(x - 7.8, y - 7.8, face - 11.6)))
        mx.append(Part.makeBox(18.2, 18.2, 9.1, App.Vector(x - 9.1, y - 9.1, face - 21.5)))
    k = Part.makeCompound([k] + mx)
    k.transformShape(_matrix("keys"))
    os.makedirs(BUILD, exist_ok=True)
    s.exportBrep(os.path.join(BUILD, "stack.brep"))
    k.exportBrep(os.path.join(BUILD, "keys.brep"))
    s.exportStep(os.path.join(BUILD, "stack.step"))
    k.exportStep(os.path.join(BUILD, "keys.step"))
    App.closeDocument(doc.Name)
    print("cache: stack", [round(v, 2) for v in s.BoundBox.__repr__ and
                           (s.BoundBox.XMin, s.BoundBox.XMax, s.BoundBox.YMin, s.BoundBox.YMax,
                            s.BoundBox.ZMin, s.BoundBox.ZMax)])
    print("cache: keys ", [round(v, 2) for v in (k.BoundBox.XMin, k.BoundBox.XMax, k.BoundBox.YMin,
                                                 k.BoundBox.YMax, k.BoundBox.ZMin, k.BoundBox.ZMax)])


def bodies():
    sp, kp = os.path.join(BUILD, "stack.brep"), os.path.join(BUILD, "keys.brep")
    if not (os.path.exists(sp) and os.path.exists(kp)):
        _build_cache()
    s, k = Part.Shape(), Part.Shape()
    s.read(sp)
    k.read(kp)
    return s, k


def clash(shape, verbose=True):
    """Volume of shape overlapping the placed models: {'stack': mm3, 'keys': mm3}."""
    out = {}
    for name, body in zip(("stack", "keys"), bodies()):
        v = 0.0
        for sol in body.Solids:
            if sol.BoundBox.intersect(shape.BoundBox):
                try:
                    v += sol.common(shape).Volume
                except Exception:
                    pass
        out[name] = round(v, 3)
    if verbose:
        print("clash mm3:", out)
    return out


def save(shape, name):
    """build/<name>.step and .stl; reports validity and solid count."""
    os.makedirs(BUILD, exist_ok=True)
    shape = shape.removeSplitter() if hasattr(shape, "removeSplitter") else shape
    shape.exportStep(os.path.join(BUILD, name + ".step"))
    import Mesh
    Mesh.Mesh(shape.tessellate(0.05)).write(os.path.join(BUILD, name + ".stl"))
    b = shape.BoundBox
    print("%s: valid=%s solids=%d volume=%.1f bbox=%s" % (
        name, shape.isValid(), len(shape.Solids), shape.Volume,
        [round(v, 2) for v in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)]))
    return shape


if os.path.basename(sys.argv[-1]) == "arcade_common.py" or __name__ == "__main__":
    _build_cache()
