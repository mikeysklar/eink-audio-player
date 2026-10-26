# Dump the Frisson board copper, pads, footprints and outline to JSON in the STEP
# frame (mm, origin board bottom-left, y up): x = kx - 99.95, y = 154.21 - ky.
import json, sys, pcbnew
OX, OY = 99.95, 154.21
src, out = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
mm = pcbnew.ToMM
P = lambda v: [round(mm(v.x) - OX, 4), round(OY - mm(v.y), 4)]
tracks = []
for t in b.GetTracks():
    tracks.append({"net": t.GetNetname(), "a": P(t.GetStart()), "b": P(t.GetEnd()), "w": round(mm(t.GetWidth()), 3), "type": t.GetClass()})
fps, pads = [], []
for f in b.GetFootprints():
    fps.append({"ref": f.GetReference(), "value": f.GetValue(), "fp": f.GetFPIDAsString(), "pos": P(f.GetPosition()),
                "rot": f.GetOrientationDegrees(), "back": f.GetLayer() == pcbnew.B_Cu})
    for p in f.Pads():
        bb = p.GetBoundingBox()
        pads.append({"ref": f.GetReference(), "num": p.GetNumber(), "net": p.GetNetname(), "pos": P(p.GetPosition()),
                     "size": [round(mm(p.GetSize().x), 3), round(mm(p.GetSize().y), 3)], "rot": p.GetOrientationDegrees(),
                     "bbox": [round(mm(bb.GetLeft()) - OX, 3), round(OY - mm(bb.GetBottom()), 3), round(mm(bb.GetRight()) - OX, 3), round(OY - mm(bb.GetTop()), 3)],
                     "drill": round(mm(p.GetDrillSize().x), 3), "smd": p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD,
                     "layers": "F" if p.IsOnLayer(pcbnew.F_Cu) else "B"})
zones = []
for z in b.Zones():
    polys = z.GetFilledPolysList(pcbnew.F_Cu)
    rings = []
    for i in range(polys.OutlineCount()):
        o = polys.Outline(i)
        ring = [P(o.CPoint(j)) for j in range(o.PointCount())]
        holes = []
        for h in range(polys.HoleCount(i)):
            hh = polys.Hole(i, h)
            holes.append([P(hh.CPoint(j)) for j in range(hh.PointCount())])
        rings.append({"outline": ring, "holes": holes})
    zones.append({"net": z.GetNetname(), "layer": z.GetLayerName(), "filled": rings})
bb = b.GetBoardEdgesBoundingBox()
json.dump({"edge_bbox": [mm(bb.GetLeft()) - OX, OY - mm(bb.GetBottom()), mm(bb.GetRight()) - OX, OY - mm(bb.GetTop())],
           "tracks": tracks, "footprints": fps, "pads": pads, "zones": zones}, open(out, "w"))
print(len(tracks), "tracks", len(fps), "fps", len(pads), "pads", len(zones), "zones")
