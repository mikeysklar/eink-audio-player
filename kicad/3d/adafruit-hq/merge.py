# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Swap the plain 'Board' body in an Adafruit_CAD_Parts STEP for a KiCad board export
(mask, silk, copper, pads), keeping every component and its colours, in the Adafruit
model's own frame.

    python merge.py adafruit.step kicad-board.step out.step [--rot DEG] [--info]
"""
import sys

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_ChildIterator, TDF_Tool
from OCP.TCollection import TCollection_AsciiString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.XCAFDoc import XCAFDoc_ColorTool, XCAFDoc_ColorGen, XCAFDoc_ColorSurf, XCAFDoc_DocumentTool
from OCP.XCAFPrs import XCAFPrs_DocumentExplorer, XCAFPrs_DocumentExplorerFlags_OnlyLeafNodes


def face_list(shape):
    out, e = [], TopExp_Explorer(shape, TopAbs_FACE)
    while e.More():
        out.append(e.Current())
        e.Next()
    return out


def face_index(faces, f):
    for i, g in enumerate(faces):
        if g.IsSame(f):
            return i
    return -1


def read(path):
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    r = STEPCAFControl_Reader()
    r.SetColorMode(True)
    r.SetNameMode(True)
    assert r.ReadFile(path) == IFSelect_RetDone, path
    r.Transfer(doc)
    return doc


def name_of(label):
    n = TDataStd_Name()
    if label.FindAttribute(TDataStd_Name.GetID_s(), n):
        return n.Get().ToExtString()
    return ""


def leaves(doc):
    """(name, located shape, colour or None, {face index: colour}, shape, location, key)
    for every leaf; key names the prototype, so repeated parts stay shared instances."""
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    out = []
    ex = XCAFPrs_DocumentExplorer(doc, XCAFPrs_DocumentExplorerFlags_OnlyLeafNodes)
    while ex.More():
        node = ex.Current()
        shape = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).GetShape_s(node.RefLabel)
        loc = node.Location
        col = node.Style.GetColorSurf() if node.Style.IsSetColorSurf() else None
        # Face colours set on sub-shape labels of the referenced shape.
        fcols = {}
        fl = face_list(shape)
        it = TDF_ChildIterator(node.RefLabel, False)
        while it.More():
            sl = it.Value()
            it.Next()
            if not XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).IsSubShape_s(sl):
                continue
            c = Quantity_Color()
            if XCAFDoc_ColorTool.GetColor_s(sl, XCAFDoc_ColorSurf, c) or XCAFDoc_ColorTool.GetColor_s(sl, XCAFDoc_ColorGen, c):
                ss = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).GetShape_s(sl)
                for f in face_list(ss):     # a face, or a shell / compound of them
                    i = face_index(fl, f)
                    if i >= 0:
                        fcols[i] = c
        entry = TCollection_AsciiString()
        TDF_Tool.Entry_s(node.RefLabel, entry)
        key = (entry.ToCString(), None if col is None else (col.Red(), col.Green(), col.Blue()))
        out.append((name_of(node.RefLabel) or name_of(node.Label), shape.Located(loc), col, fcols,
                    shape, loc, key))
        ex.Next()
    return out


def bbox(shape):
    b = Bnd_Box()
    BRepBndLib.Add_s(shape, b, True)
    lo, hi = b.CornerMin(), b.CornerMax()
    return (lo.X(), lo.Y(), lo.Z(), hi.X(), hi.Y(), hi.Z())


def volume(shape):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, p)
    return p.Mass()


def main():
    a_path, k_path, out_path = sys.argv[1:4]
    rot = float(sys.argv[sys.argv.index("--rot") + 1]) if "--rot" in sys.argv else 0.0
    ada, kic = leaves(read(a_path)), leaves(read(k_path))
    board = [x for x in ada if x[0] == "Board"]
    assert len(board) == 1, [x[0] for x in ada][:20]
    bshape = board[0][1]
    ax = bbox(bshape)
    print("adafruit Board bbox", [round(v, 3) for v in ax], "vol %.1f" % volume(bshape))
    # The KiCad board body: the largest solid in the export.
    kbody = max(kic, key=lambda x: volume(x[1]))
    t = gp_Trsf()
    if rot:
        t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), rot * 3.141592653589793 / 180)
    kb = kbody[1].Moved(TopLoc_Location(t))
    kx = bbox(kb)
    print("kicad body bbox", [round(v, 3) for v in kx], "vol %.1f" % volume(kb))
    # Line up x/y centres and the bottom faces.
    move = gp_Trsf()
    move.SetTranslation(gp_Vec((ax[0] + ax[3]) / 2 - (kx[0] + kx[3]) / 2,
                               (ax[1] + ax[4]) / 2 - (kx[1] + kx[4]) / 2, ax[2] - kx[2]))
    move.Multiply(t)
    whole = TopLoc_Location(move)
    common = volume(BRepAlgoAPI_Common(kbody[1].Moved(whole), bshape).Shape())
    iou = common / (volume(kbody[1]) + volume(bshape) - common)
    print("fit IoU %.3f  size adafruit %.2f x %.2f  kicad %.2f x %.2f" % (
        iou, ax[3] - ax[0], ax[4] - ax[1], kx[3] - kx[0], kx[4] - kx[1]))
    if "--info" in sys.argv:
        return

    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    root = st.NewShape()
    TDataStd_Name.Set_s(root, TCollection_ExtendedString(out_path.rsplit("/", 1)[-1][:-5]))
    protos = {}
    n = 0
    items = [x + ("a",) for x in ada if x[0] != "Board"] + [x + ("k",) for x in kic]
    for name, _, col, fcols, shape, loc, key, src in items:
        key = (src,) + key
        if key not in protos:
            lab = st.AddShape(shape, False)
            if name:
                TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
            if col is not None:
                ct.SetColor(lab, col, XCAFDoc_ColorSurf)
            if fcols:
                fl = face_list(shape)
                for i, c in fcols.items():
                    sl = st.AddSubShape(lab, fl[i])
                    if not sl.IsNull():
                        ct.SetColor(sl, c, XCAFDoc_ColorSurf)
            protos[key] = lab
        st.AddComponent(root, protos[key], whole.Multiplied(loc) if src == "k" else loc)
        n += 1
    st.UpdateAssemblies()
    from OCP.Interface import Interface_Static
    Interface_Static.SetIVal_s("write.surfacecurve.mode", 0)   # no pcurves: half the size
    w = STEPCAFControl_Writer()
    w.SetColorMode(True)
    w.SetNameMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    assert w.Write(out_path) == IFSelect_RetDone
    print("wrote", out_path, n, "instances of", len(protos), "shapes")


main()
