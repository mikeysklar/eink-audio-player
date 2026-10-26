# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Writes its outputs next to itself (scripts/). Used to generate the board; copy the outputs into kicad/ to use them.
"""Placement-only layout for the Feather RP2350 audio landing pad.

Header-only version: the Feather and the DAC breakout plug into SMT female
sockets. The display is a 2.13" quad-colour e-ink (Adafruit 6366, JD79661) on an
EYESPI flex, driven from the Feather's SPI pins; its own microSD (SPI) holds
the music, so there is no HSTX input and no SDIO socket any more.

  6000 Feather RP2350
  6309 TLV320DAC3100 I2S DAC breakout
  5613 EYESPI breakout, its flex to the 6366 display on the back
  2000 mAh LiPo (Adafruit 2011) between the PCB and the display

Header coordinates come from each board's Eagle .brd (origin bottom-left,
y up). The Adafruit_CAD_Parts STEP models share that origin with the PCB
bottom at z=0, so each breakout is a pad-less footprint anchored at its
Eagle origin that carries the model, and its sockets are stock footprints
placed through the same transform. No nets or routing yet.

The discrete-parts first pass is kept in build_pcb_v1_discrete.py.

Run with KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 build_pcb.py
"""

import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "frisson.kicad_pcb")
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

# Board dimensions first, everything else derives from them.
BX, BY = 100.0, 100.0  # sheet offset of the board's top-left corner
# Width is the 2.13in display's (60.96 x 39.37). The Feather and TLV stack in
# a right-hand column below the EYESPI breakout, which sets the height:
# FTH_Y is the Feather's top edge, below BY.
DISP_W, DISP_H = 60.96, 39.37
FTH_Y = 1.9
# EDGE_FILL keeps the edge pads far enough in for the GND fill to pass
# outside them (0.5 edge, 0.5 fill, 0.4 gap), so the fill rings the board
# for the laser. H puts the TLV's bottom socket pads (J9) that far in.
EDGE_FILL = 1.4
W, H = DISP_W, 54.16
CORNER_R = 3.0
# The outline runs EXTRA_L past the display's left edge. Everything else is
# placed from BX (the display's left edge); only the outline uses EDGE_X.
# 0 now: nothing runs down the left edge, so the sides are flush with the
# display's.
EXTRA_L = 0.0
EDGE_X = BX - EXTRA_L
# The outline also runs EXTRA_T above BY for the EYESPI breakout (5613) on
# the top edge: EDGE_FILL, its two socket rows 12.7 apart (pads reach 2.6
# either side of a row), then three lanes above J1's pads.
EXTRA_T = 21.9
EDGE_Y = BY - EXTRA_T

# Stock SMD socket model is 7.4 mm tall; a male header's plastic adds 2.5 mm.
STACK_Z = 7.4 + 2.5

board = pcbnew.BOARD()


def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def place(lib, name, ref, value, x, y, rot=0.0):
    fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)
    if fp is None:
        raise RuntimeError(f"footprint not found: {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    board.Add(fp)
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(rot)
    return fp


def line(x1, y1, x2, y2, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(mm(x1, y1))
    s.SetEnd(mm(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    board.Add(s)


def arc(cx, cy, sx, sy, deg, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetCenter(mm(cx, cy))
    s.SetStart(mm(sx, sy))
    s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(deg, pcbnew.DEGREES_T), True)
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    board.Add(s)


def text(s, x, y, layer, size=1.0, rot=0.0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(mm(x, y))
    t.SetLayer(layer)
    t.SetTextSize(mm(size, size))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    t.SetTextAngleDegrees(rot)
    board.Add(t)


class Module:
    """A plug-in board anchored at its Eagle origin, rotated rot degrees CCW."""

    def __init__(self, ref, value, step, w, h, ax, ay, rot, z=None):
        self.ax, self.ay, self.rot = ax, ay, rot
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        # Outline in footprint-local coords: eagle (ex, ey) -> (ex, -ey).
        corners = ((0, 0), (w, 0), (w, h), (0, h), (0, 0))
        for (x1, y1), (x2, y2) in zip(corners, corners[1:]):
            for layer in (pcbnew.F_Fab, pcbnew.F_SilkS):
                s = pcbnew.PCB_SHAPE(fp)
                s.SetShape(pcbnew.SHAPE_T_SEGMENT)
                s.SetStart(mm(x1, -y1))
                s.SetEnd(mm(x2, -y2))
                s.SetLayer(layer)
                s.SetWidth(pcbnew.FromMM(0.12))
                fp.Add(s)
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = "${KIPRJMOD}/3d/" + step
        m.m_Offset = pcbnew.VECTOR3D(0, 0, STACK_Z if z is None else z)
        fp.Models().push_back(m)
        board.Add(fp)
        fp.SetPosition(mm(ax, ay))
        fp.SetOrientationDegrees(rot)

    def xy(self, ex, ey):
        """Eagle board coords -> KiCad sheet coords."""
        lx, ly = ex, -ey
        t = math.radians(self.rot)
        return (self.ax + lx * math.cos(t) + ly * math.sin(t),
                self.ay - lx * math.sin(t) + ly * math.cos(t))

    def socket(self, ref, value, n, pin1, pin2):
        """Stock SMD socket under a header, given its pin 1 and pin 2 in eagle coords."""
        (x1, y1), (x2, y2) = self.xy(*pin1), self.xy(*pin2)
        dx, dy = x2 - x1, y2 - y1
        # Stock socket runs pin 1 -> N along local +y, i.e. (sin r, cos r) on the sheet.
        rot = math.degrees(math.atan2(dx, dy))
        half = (n - 1) / 2
        return place("Connector_PinSocket_2.54mm",
                     f"PinSocket_1x{n:02d}_P2.54mm_Vertical_SMD_Pin1Left",
                     ref, value, x1 + dx * half, y1 + dy * half, rot)


# --- outline, rounded corners ---
EC = pcbnew.Edge_Cuts
r = CORNER_R
line(EDGE_X + r, EDGE_Y, BX + W - r, EDGE_Y, EC)
line(BX + W, EDGE_Y + r, BX + W, BY + H - r, EC)
line(BX + W - r, BY + H, EDGE_X + r, BY + H, EC)
line(EDGE_X, BY + H - r, EDGE_X, EDGE_Y + r, EC)
arc(EDGE_X + r, EDGE_Y + r, EDGE_X, EDGE_Y + r, 90, EC)
arc(BX + W - r, EDGE_Y + r, BX + W - r, EDGE_Y, 90, EC)
arc(BX + W - r, BY + H - r, BX + W, BY + H - r, 90, EC)
arc(EDGE_X + r, BY + H - r, EDGE_X + r, BY + H, 90, EC)

# Hand-held orientation, looking at the component side:
#   top edge    the display flex wraps off the EYESPI breakout (5613) to
#               the back
#   right edge  every plug and port: power switch (SW1), USB-C, headphone jack
#   back side   2000 mAh LiPo, then the 2.13" e-ink (screen facing out) at
#               the top and the NeoKey 1x4 (keys facing out) below it; no
#               parts on the back, all are drawn there for the 3D view. The
#               NeoKey chains off the Feather's own STEMMA QT port, so the
#               landing pad has no I2C connectors of its own.
#
# Mounting: the display's four M2.5 holes (the top two are the board's top
# corners), the Feather's corner hole, the TLV's corner hole and the
# bottom-left corner. The case holds the NeoKey.

# --- Feather RP2350, top-right, rotated 180 so USB-C is on the right edge.
# Its corner flush with the display's, so its USB-end top hole is the
# display's top-right hole. ---
FEATHER_W, FEATHER_H = 50.8, 22.86
feather = Module("A1", "Feather RP2350 (6000)", "6000 Feather RP2350.step",
                 FEATHER_W, FEATHER_H, BX + W, BY + FTH_Y, 180)
# JP1 16-pin: pad 1 (PSRAM_CS) at x=44.45, pad 16 (!RESET) at the USB end.
feather.socket("J1", "Feather 16-pin", 16, (44.45, 1.27), (41.91, 1.27))
# JP3 12-pin: pad 1 VBAT at x=16.51, pad 12 SDA at x=44.45.
feather.socket("J2", "Feather 12-pin", 12, (16.51, 21.6535), (19.05, 21.6535))

# --- 6309 TLV320DAC3100 breakout, bottom right, unrotated so the headphone
# jack (eagle x=31.75..33.54) pokes out of the right edge. 50.8 mm below the
# Feather's top leaves room for both socket courtyards. ---
TLV_W = 31.75
tlv = Module("A3", "TLV320DAC3100 breakout (6309)", "6309 TLV320DAC3100 I2S DAC.step",
             TLV_W, 25.4, BX + W - TLV_W, BY + FTH_Y + 50.8, 0)
tlv.socket("J9", "TLV VIN..SPKP", 10, (1.905, 2.54), (4.445, 2.54))
tlv.socket("J10", "TLV MICBIAS..MIC", 8, (6.985, 22.86), (9.525, 22.86))

# --- right edge, on the landing pad: SW1 between the display's bottom-right
# hole and the TLV. ---
# Power switch: MSK-12C03 side-actuated slide (as on grippy). Rot 90 points
# the actuator (local +y) out of the right edge; the body front (local y=2.05)
# sits on the edge so a printed slider in the case can grab it.
sw = pcbnew.FootprintLoad(os.path.join(HERE, "frisson.pretty"), "SW_SPDT_MSK-12C03")
sw.SetReference("SW1")
sw.SetValue("Power (MSK-12C03)")
board.Add(sw)
# Its body (3.9 either side of centre) clears the hole's M2.5 head (2.25).
DS_Y = EDGE_Y   # display's top edge, flush with the board's
sw.SetPosition(mm(BX + W - 2.05, DS_Y + DISP_H - 2.54 + 2.25 + 3.9 + 0.2))
sw.SetOrientationDegrees(90)
# --- Adafruit EYESPI breakout (5613), 25.4 x 17.78, on the top edge, face
# up. Its FPC (eagle 12.7, 10.414) is centred, so centring the breakout puts
# it straight in line with the display's own connector (display x 30.48).
# Rot 180 opens the FPC toward the top edge. Adafruit's cable is A-B (pin 1
# to pin 1) and made for both boards' parts facing the same way with the
# cable flat between them; folding the display under round the top edge is
# that same layout, with the display's screen facing out (turned 180;
# rotation=180 in software). Eagle JP2 (EYESPI 1-9) lands on the lower row,
# J4, JP1 (10-18) on the upper row, J5. Its two plated holes would sit in
# the lanes between the rows, so the sockets alone hold it. ---
EYE_W, EYE_H = 25.4, 17.78
eye = Module("A7", "EYESPI breakout (5613)", "5613 EYESPI Breakout.step",
             EYE_W, EYE_H, BX + W / 2 + EYE_W / 2, EDGE_Y + EDGE_FILL + 2.6 - 2.54, 180)
eye.socket("J4", "EYESPI 1-9 (5613 JP2)", 9, (22.86, 15.24), (20.32, 15.24))
eye.socket("J5", "EYESPI 10-18 (5613 JP1)", 9, (22.86, 2.54), (20.32, 2.54))


def back_block(ref, value, step, l, w, z, cx, cy, rot=(0, 0, 0), off=(0, 0), turn=0, flip=True):
    """Pad-less footprint on the back carrying a placeholder box, z below the board.
    No courtyard: the battery and display stack, and nothing else is on the back."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    rr = pcbnew.PCB_SHAPE(fp)
    rr.SetShape(pcbnew.SHAPE_T_RECT)
    rr.SetStart(mm(-l / 2, -w / 2))
    rr.SetEnd(mm(l / 2, w / 2))
    rr.SetLayer(pcbnew.F_Fab)
    rr.SetWidth(pcbnew.FromMM(0.12))
    fp.Add(rr)
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/3d/" + step
    m.m_Offset = pcbnew.VECTOR3D(off[0], off[1], z)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    fp.Models().push_back(m)
    board.Add(fp)
    fp.SetPosition(mm(cx, cy))
    fp.SetOrientationDegrees(turn)
    if flip:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    return fp


DISP_CX, DISP_CY = BX + W / 2, DS_Y + DISP_H / 2

# --- back side: Adafruit 2011 LiPo, 2000 mAh, real Adafruit_CAD_Parts model:
# one 37 x 60 x 7.5 block, protection end included. Standing lengthwise,
# centred on the board: between the standoff columns (x 112-149 against
# 102.5/158.4, ~7 mm clear each side) and 8 mm in from the top and bottom
# edges. The display's parts (EINK_T) and the NeoKey's sockets sit on it. ---
BAT_T = 7.5
BAT_L = 60.0
BAT_Y0 = (EDGE_Y + BY + H - BAT_L) / 2
back_block("BT1", "LiPo 2000 mAh (Adafruit 2011)", "2011 2000mAh Battery.step",
           37.0, BAT_L, 0, BX + W / 2, BAT_Y0 + BAT_L / 2)

# Display: Adafruit 6366, 2.13in quad-colour EYESPI (JD79661), 60.96 x 39.37, real
# Adafruit_CAD_Parts model. Its parts are +z (to 3.46) and the panel -z;
# flipped 180 about Y so the parts face the battery, the screen faces out,
# turned 180 in plane so the EYESPI edge is at the board's top edge where
# the EYESPI flex wraps. Flush with the top edge, so the fold is short.
# EINK_T is its parts' height, so they just clear the battery.
EINK_T = 3.5
back_block("DS1", "2.13in quad-colour e-ink (Adafruit 6366)",
           "6366 2.13in Tri-Color eInk.step", DISP_W, DISP_H, BAT_T + EINK_T,
           DISP_CX, DISP_CY, rot=(0, 180, 0), off=(DISP_W / 2, -DISP_H / 2), turn=180)

# --- NeoKey 1x4 QT (4980), reference only (no pads, no copper), the only
# buttons; it chains off the Feather's STEMMA QT port. On the back below the
# display, keys facing out the same way as the screen, its hot-swap sockets
# (+z in the model, to NK4_D) on the battery.
# 76.2 x 21.59, so it overhangs the board 7.6 each side; the case holds it.
NK4_W, NK4_H, NK4_D = 76.2, 21.59, 4.53     # D: PCB + sockets
# Centred between the display's bottom edge and the board's (7.6 clear each
# way), so a printed case can wrap round it. Its sockets sit on the battery.
NK4_Z = BAT_T
NK4_Y = (DS_Y + DISP_H + BY + H) / 2
nk4 = back_block("A5", "NeoKey 1x4 QT (4980), case-mounted", "4980 NeoKey 1x4 QT.step",
                 NK4_W, NK4_H, NK4_Z + NK4_D, BX + W / 2, NK4_Y,
                 rot=(0, 180, 0), off=(NK4_W / 2, -NK4_H / 2), turn=180)
# Four Cherry MX switches with keycaps (3d/make_mx_wrl.py), on the 1x4's
# 19.05 pitch, centred on its width (model y 10.79), standing on its top face.
for kx in (-28.575, -9.525, 9.525, 28.575):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/3d/Cherry MX keycap.wrl"
    m.m_Offset = pcbnew.VECTOR3D(kx, 0, NK4_Z + NK4_D)
    nk4.Models().push_back(m)

# --- ANO rotary encoder (6310), reference only: it is not on this board but on the
# stand's ano_mount (arcade/parts/ano_mount.py), past the right-hand end of the keys and
# toward the player, in the keys' plane. Placed where the stand puts it relative to the
# NeoKey (board frame, from arcade's layout.json keys matrix), so the 3D view shows the
# whole control layout: off the board, beyond its bottom-left corner. Its STEMMA QT
# chains off the NeoKey's. Wheel facing out with the keys.
ANO_DX, ANO_DY = -63.82, 36.885                 # its centre from the NeoKey's
ANO_Z = 21.66                                   # its PCB front, below the board
back_block("ANO1", "ANO rotary encoder (6310), stand-mounted, reference",
           "5740 ANO Rotary Encoder QT.step", 40.64, 35.56, ANO_Z,
           BX + W / 2 + ANO_DX, NK4_Y + ANO_DY, rot=(180, 0, 90))

# --- mounting holes on the display's pattern (2.54 mm in from its corners;
# the top two are the board's top corners, beside the EYESPI breakout), the
# Feather's corner hole, the TLV's corner hole at bottom-right and one on bare
# board at bottom-left. ---
HOLE_TL = (BX + 2.54, DS_Y + 2.54)
HOLE_TR = (BX + W - 2.54, DS_Y + 2.54)
HOLE_BL = (BX + 2.54, DS_Y + DISP_H - 2.54)
HOLE_BR = (BX + W - 2.54, DS_Y + DISP_H - 2.54)
HOLE_FTH = feather.xy(2.54, 2.54)
HOLE_TLV = tlv.xy(29.21, 2.54)
HOLE_CORNER_BL = (BX + 2.54, HOLE_TLV[1])
for i, (x, y) in enumerate((HOLE_TL, HOLE_TR, HOLE_BL, HOLE_BR, HOLE_FTH, HOLE_TLV,
                            HOLE_CORNER_BL)):
    h = place("MountingHole", "MountingHole_2.7mm", f"H{i + 1}", "M2.5", x, y)
    h.Reference().SetVisible(False)
    for hp in h.Pads():
        hp.SetLocalClearance(pcbnew.FromMM(0.1))   # the GND fill only; traces keep 1.0

# --- labels ---
SILK = pcbnew.F_SilkS
text("Feather RP2350", *feather.xy(40.0, 15.5), SILK, 1.2)  # under the Feather, clear of R8 (it is turned 180)
text("TLV320DAC3100", *tlv.xy(18.0, 19.0), SILK, 1.0)
# The traps: nothing on the board says these, and each fails quietly.
# In the bare patch west of the breakout, clear of the corner hole.
text("EYESPI 5613", EDGE_X + 9.5, EDGE_Y + 6.5, SILK, 1.0)
text("FPC to edge", EDGE_X + 9.5, EDGE_Y + 8.3, SILK, 1.0)
text("e-ink", EDGE_X + 9.5, EDGE_Y + 11.3, SILK, 1.0)
text("rotation=180", EDGE_X + 9.5, EDGE_Y + 13.1, SILK, 1.0)
# I2S pins on J9, in the bare corner under the TLV east of its I2S lanes
text("I2S on", *tlv.xy(23.0, 10.0), SILK, 0.8)
text("A0 A1 A2", *tlv.xy(23.0, 8.8), SILK, 0.8)
DW = pcbnew.Dwgs_User
text("NeoKey 1x4 along this edge (case-mounted); display flex wraps here",
     BX + W / 2, EDGE_Y - 2.0, DW, 1.2)
text("power, USB-C, jack", BX + W + 2.0, BY + H / 2, DW, 1.2, 90)
text("back: LiPo 2000 mAh + 2.13in e-ink (turned 180)", BX + W / 2, BY + H + 2.0, DW, 1.2)

# --- schematic links, nets, routes ---------------------------------------
# netlist.py says which pad is on which net, plan.py where the copper runs,
# gen_sch.py the symbol UUIDs (uuid5 of the reference) the footprints link to.
import json  # noqa: E402

import check_plan  # noqa: E402
import gen_sch  # noqa: E402
import netlist  # noqa: E402
import plan  # noqa: E402

LIB_OF = {"J1": "Connector_PinSocket_2.54mm", "J2": "Connector_PinSocket_2.54mm",
          "J9": "Connector_PinSocket_2.54mm", "J10": "Connector_PinSocket_2.54mm",
          "J4": "Connector_PinSocket_2.54mm", "J5": "Connector_PinSocket_2.54mm",
          "SW1": "frisson"}
PIN_NAME = {"SW1": {"1": "A", "2": "B", "3": "C"}}
# Render-only parts: no symbol, out of BOM, position files and parity.
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref in ("A1", "A3", "A5", "A7", "DS1", "BT1", "ANO1"):
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        # Their outlines are for looking at, not for the laser.
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                g.SetLayer(pcbnew.F_Fab)
        continue
    if ref == "SW1":
        fp.GetField("Description").SetText("")  # schematic has none
    lib = LIB_OF.get(ref, "MountingHole" if ref.startswith("H") else None)
    fp.SetFPID(pcbnew.LIB_ID(lib, fp.GetFPID().GetLibItemName().wx_str()))
    fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.uid(ref)))

nets = {}


def net(name):
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
    return nets[name]


pads = {}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        b = pad.GetBoundingBox()
        pads.setdefault((fp.GetReference(), pad.GetNumber()), []).append(
            (pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()),
             pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom())))
tracks, jumpers = plan.routes(pads)
# Each 0R splits its net in two (KiCad sees a part between two nets).
pad_sub, jp_sub, trk_sub = check_plan.split_nets(pads, tracks, jumpers)

for fp in board.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        num = pad.GetNumber()
        if not num:
            continue  # NPTH
        if (ref, num) in pad_sub:
            pad.SetNet(net("/" + pad_sub[(ref, num)]))
        elif ref in LIB_OF:
            pin = PIN_NAME.get(ref, {}).get(num, f"Pin_{num}")
            pad.SetNet(net(f"unconnected-({ref}-{pin}-Pad{num})"))


def add_track(a, b, name, width):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(mm(*a))
    t.SetEnd(mm(*b))
    t.SetWidth(pcbnew.FromMM(width))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net("/" + name))
    board.Add(t)


for t, sub in zip(tracks, trk_sub):
    pts = plan.miter(t["pts"], t["chamfer"])
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) > 1e-6:
            add_track(a, b, sub, t["w"])

# gen_sch.py reads this back: every connected pad's (sub-)net.
sch_nets = {f"{r}.{n}": v for (r, n), v in pad_sub.items()}

# 0R jumpers: stock 0805, rotated 90 when the hop runs along y.
for j in jumpers:
    fp = place("Resistor_SMD", "R_0805_2012Metric", j["ref"], "0R", *j["center"],
               0 if j["horiz"] else 90)
    fp.SetFPID(pcbnew.LIB_ID("Resistor_SMD", "R_0805_2012Metric"))
    fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.uid(j["ref"])))
    fp.Value().SetVisible(False)
    # The jumpers sit 2.54 apart, too close for silk labels: fab layer only.
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Reference().SetTextSize(mm(0.5, 0.5))
    fp.Reference().SetTextThickness(pcbnew.FromMM(0.08))
    fp.Reference().SetPosition(mm(*j["center"]))
    fp.Reference().SetTextAngleDegrees(0)
    for pad in fp.Pads():
        p = pad.GetPosition()
        side = min("ab", key=lambda k: math.dist(j["p" + k], (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))))
        sub = jp_sub[(j["ref"], side)]
        pad.SetNet(net("/" + sub))
        sch_nets[f"{j['ref']}.{pad.GetNumber()}"] = sub

# --- design rules ----------------------------------------------------------
# 0.4 mm traces and 0.4 mm gaps everywhere (netclass, kept in the .kicad_pro
# that kicad-cli reads). Exceptions in the rule file: 0.2 at the 0805
# jumpers' pads, 1.0 from the screw holes for traces, 0.6 for the fill.
ds = board.GetDesignSettings()
ds.m_MinClearance = pcbnew.FromMM(0.1)
ds.m_TrackMinWidth = pcbnew.FromMM(0.4)
ds.m_CopperEdgeClearance = pcbnew.FromMM(0.1)   # the fill; the rule file keeps the rest at 0.5

# GND fill over the rest of F.Cu, solid onto GND pads (no thermals), islands
# kept, a closed ring round the board for the laser.
FILL_GAP = 0.4   # the netclass gap; KiCad checks the fill against it
HOLE_FILL_GAP = 0.1
EDGE_FILL_GAP = 0.1
r_in = CORNER_R - EDGE_FILL_GAP


def fill(name, priority, islands):
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.F_Cu)
    zone.SetNet(net("/" + name))
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(pcbnew.FromMM(FILL_GAP))
    zone.SetMinThickness(pcbnew.FromMM(0.5))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetIslandRemovalMode(islands)
    outline = zone.Outline()
    outline.NewOutline()
    for cx, cy, a0 in ((BX + W - r, BY + H - r, 0), (EDGE_X + r, BY + H - r, 90),
                       (EDGE_X + r, EDGE_Y + r, 180), (BX + W - r, EDGE_Y + r, 270)):
        for k in range(9):
            t = math.radians(a0 + 90 * k / 8)
            outline.Append(pcbnew.FromMM(cx + r_in * math.cos(t)),
                           pcbnew.FromMM(cy + r_in * math.sin(t)))
    board.Add(zone)


fill(plan.POUR, 0, pcbnew.ISLAND_REMOVAL_MODE_NEVER)
# Each pocket's fill: the whole board again, filled first, then all but the
# piece holding the pocket's pads dropped.
for name in plan.POCKETS:
    fill(name, 1, pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
# The fill keeps 0.1 off the screw holes (the rule file's "screw head on
# fill" rule, which the script's filler does not read): a no-fill keepout
# each, and the hole's own clearance cut to match. The head sits on GND, and
# the fill passes between each hole and the edge, so the ring stays closed.
for fp in board.GetFootprints():
    if fp.GetReference().startswith("H"):
        c = fp.GetPosition()
        ko = pcbnew.ZONE(board)
        ko.SetIsRuleArea(True)
        ko.SetLayer(pcbnew.F_Cu)
        ko.SetDoNotAllowZoneFills(True)
        ko.SetDoNotAllowTracks(False)
        ko.SetDoNotAllowVias(False)
        ko.SetDoNotAllowPads(False)
        ko.SetDoNotAllowFootprints(False)
        o = ko.Outline()
        o.NewOutline()
        rk = 1.35 + HOLE_FILL_GAP + 0.05
        for k in range(24):
            t = 2 * math.pi * k / 24
            o.Append(c.x + pcbnew.FromMM(rk * math.cos(t)), c.y + pcbnew.FromMM(rk * math.sin(t)))
        board.Add(ko)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

pcbnew.SaveBoard(OUT, board)
print("wrote", OUT, f"{len(tracks)} tracks, {len(jumpers)} jumpers")
json.dump(sch_nets, open(os.path.join(HERE, "subnets.json"), "w"), indent=1, sort_keys=True)

pro = os.path.join(HERE, "frisson.kicad_pro")
d = json.load(open(pro))
rules = d["board"]["design_settings"]["rules"]
rules.update({"min_clearance": 0.1, "min_track_width": 0.4,
              "min_copper_edge_clearance": 0.1})
for nc in d["net_settings"]["classes"]:
    if nc["name"] == "Default":
        nc.update({"clearance": 0.4, "track_width": 0.4})
json.dump(d, open(pro, "w"), indent=2)
open(os.path.join(HERE, "frisson.kicad_dru"), "w").write("""(version 1)
# An 0805's pads are 0.8 mm apart, so the 0.4 track it hops keeps 0.2.
(rule "0805 jumpers"
\t(condition "A.memberOfFootprint('R*') || B.memberOfFootprint('R*')")
\t(constraint clearance (min 0.2mm)))
# M2.5 screw heads (4.5 mm) reach 0.9 past the 2.7 mm holes.
(rule "screw heads"
\t(condition "A.memberOfFootprint('H*') || B.memberOfFootprint('H*')")
\t(constraint hole_clearance (min 1.0mm)))
# The GND fill runs to 0.1 of a hole (under the head) and of the edge, so it
# rings the board unbroken. Everything else keeps 0.4 to the holes' copper-free
# pads and 0.5 to the edge.
(rule "screw head on fill"
\t(condition "(A.memberOfFootprint('H*') && B.Type == 'Zone') || (B.memberOfFootprint('H*') && A.Type == 'Zone')")
\t(constraint hole_clearance (min 0.1mm))
\t(constraint clearance (min 0.1mm)))
(rule "holes, not fill"
\t(condition "(A.memberOfFootprint('H*') && B.Type != 'Zone') || (B.memberOfFootprint('H*') && A.Type != 'Zone')")
\t(constraint clearance (min 0.4mm)))
(rule "edge, not fill"
\t(condition "A.Type != 'Zone' && B.Type != 'Zone'")
\t(constraint edge_clearance (min 0.5mm)))
# 0R jumpers sit under the breakouts (they ride 8.5 mm up). H2/H5 are the
# Feather's and TLV's own holes, so their courtyards meet the sockets'.
(rule "jumpers and holes"
\t(condition "A.Reference == 'R*' || A.Reference == 'H*' || B.Reference == 'R*' || B.Reference == 'H*'")
\t(constraint courtyard_clearance)
\t(severity ignore))
""")
