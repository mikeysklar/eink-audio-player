# Adafruit EYESPI breakout (5613) for the eink-audio-player's 3D view, Eagle
# coords (origin bottom-left, y up). Adafruit_CAD_Parts has no 5613 model,
# so it is assembled from:
#   board, holes   Adafruit-EYESPI-PCB .brd (25.4 x 17.78, r2.54 corners,
#                  2.5 holes at 2.54/22.86, 8.89)
#   FPC connector  the same EYE_SPI_DISPLAY_BOTCONTACT part cut out of
#                  Adafruit_CAD_Parts' 6366 display model, placed at the
#                  .brd's X1 (12.7, 10.414), pads toward +y
#   headers        KiCad's stock PinHeader_1x09, under the board, at JP1
#                  (y 2.54) and JP2 (y 15.24), pin 1 at x 22.86
import os
import FreeCAD, Part, Import
V = FreeCAD.Vector
SP = "/private/tmp/claude-501/-Volumes-clear-Downloads-ada-hstx-audio/58cddaf7-e716-40c6-a9b6-4e2a8536ad9a/scratchpad/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "5613 EYESPI Breakout.step")
T = 1.6
r = 2.54
w, h = 25.4, 17.78
board = Part.makeBox(w, h, T)
board = board.makeFillet(r, [e for e in board.Edges
                             if abs(e.Vertexes[0].Point.x - e.Vertexes[1].Point.x) < 1e-6
                             and abs(e.Vertexes[0].Point.y - e.Vertexes[1].Point.y) < 1e-6])
for x in (2.54, 22.86):
    board = board.cut(Part.makeCylinder(1.25, T, V(x, 8.89, 0)))

conn = Part.read(SP + "eyeconn.step")
# in the display model: pads at -y, centre x 30.48, package origin y 32.36, base z 1.57
m = FreeCAD.Matrix()
m.move(V(-30.48, -32.36, -1.57))
m.rotateZ(3.141592653589793)
m.move(V(12.7, 10.414, T))
conn = conn.transformGeometry(m)

hdr = Part.read("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels/"
                "Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x09_P2.54mm_Vertical.step")
print("hdr bb", hdr.BoundBox)
parts = [board, conn]
for yrow in (2.54, 15.24):
    hm = FreeCAD.Matrix()
    hm.rotateX(3.141592653589793)
    hm.rotateZ(3.141592653589793 / 2)
    hm.move(V(22.86, yrow, 0))
    parts.append(hdr.transformGeometry(hm))
doc = FreeCAD.newDocument("b")
objs = []
for name, sh in zip(("board", "fpc", "jp1", "jp2"), parts):
    o = doc.addObject("Part::Feature", name)
    o.Shape = sh
    objs.append(o)
    print(name, [round(v, 2) for v in (sh.BoundBox.XMin, sh.BoundBox.XMax, sh.BoundBox.YMin,
                                      sh.BoundBox.YMax, sh.BoundBox.ZMin, sh.BoundBox.ZMax)])
Import.export(objs, OUT)
