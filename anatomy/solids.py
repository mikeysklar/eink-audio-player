import FreeCAD, Import, json, os
doc = FreeCAD.newDocument("m")
Import.insert(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "enclosure", "inputs", "board.step"), doc.Name)
def top(o):
    path = []
    q = o
    while q.InList:
        q = q.InList[0]
        path.append(q.Label)
    return path[::-1]
out = []
for o in doc.Objects:
    if o.TypeId != "Part::Feature" or o.Shape.isNull(): continue
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); b = s.BoundBox
    out.append({"label": o.Label, "path": top(o), "bb": [round(v, 3) for v in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)], "vol": round(o.Shape.Volume, 2)})
json.dump(out, open("solids.json", "w"))
print(len(out))
