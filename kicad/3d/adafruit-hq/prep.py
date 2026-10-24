# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
import sys, pcbnew
path = sys.argv[1]
s = open(path).read()
s = s.replace('(layer "UNDEFINED")', '(layer "Cmts.User")')
if "(stackup" not in s:
    s = s.replace("(setup", """(setup
    (stackup
        (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
        (layer "F.Paste" (type "Top Solder Paste"))
        (layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
        (layer "F.Cu" (type "copper") (thickness 0.035))
        (layer "dielectric 1" (type "core") (color "FR4 natural") (thickness 1.51)
            (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
        (layer "B.Cu" (type "copper") (thickness 0.035))
        (layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
        (layer "B.Paste" (type "Bottom Solder Paste"))
        (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
        (copper_finish "ENIG")
        (dielectric_constraints no))""", 1)
open(path, "w").write(s)
b = pcbnew.LoadBoard(path)
for fp in b.GetFootprints():
    fp.Models().clear()
zones = b.Zones()
pcbnew.ZONE_FILLER(b).Fill(zones)
bb = b.GetBoardEdgesBoundingBox()
print("edges", round(pcbnew.ToMM(bb.GetX()), 3), round(pcbnew.ToMM(bb.GetY()), 3),
      round(pcbnew.ToMM(bb.GetWidth()), 3), round(pcbnew.ToMM(bb.GetHeight()), 3),
      "fps", len(b.GetFootprints()), "zones", len(zones), "tracks", len(b.GetTracks()))
b.Save(path)
