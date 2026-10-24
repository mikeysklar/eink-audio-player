#!/bin/zsh
# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Adafruit EYESPI breakout (5613) STEP, built from Adafruit's own board. Adafruit_CAD_Parts
# has no 5613 model, so:
#   board    Adafruit-EYESPI-PCB .brd, imported into KiCad: real outline, copper, pads,
#            plated holes and silkscreen, with a black-mask / white-silk / ENIG stackup
#   X1       KiCad's stock Hirose FH12-18S-0.5SH (18 pin, 0.5 mm FPC), same size and place
#            as the board's EYE_SPI_DISPLAY_BOTCONTACT
#   JP1/JP2  KiCad's stock PinHeader_1x09, under the board, pin 1 at x 22.86
# Frame: Eagle's, origin at the board's bottom-left, y up, board top at z 1.6, the same as
# the stand-in it replaces, so the landing pad footprint needs no new offset.
#   ./make_5613_step.sh            writes "5613 EYESPI Breakout.step" next to this file
set -e
HERE=${0:A:h}
CLI=${CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
KP=${KP:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
W=$(mktemp -d)
curl -sfL -o $W/eyespi.brd \
    "https://raw.githubusercontent.com/adafruit/Adafruit-EYESPI-PCB/main/Adafruit%20EYESPI%20Breakout%20Board.brd"
"$CLI" pcb import --format eagle -o $W/eyespi.kicad_pcb $W/eyespi.brd > /dev/null
# Eagle's fiducial mask rings and dimensions land on no KiCad layer; the exporter refuses them.
sed -i '' 's/(layer "UNDEFINED")/(layer "Cmts.User")/' $W/eyespi.kicad_pcb
"$KP" - $W/eyespi.kicad_pcb <<'EOF' 2>&1 | grep -v -i -E "traits|wxApp" || true
import sys
import pcbnew

path = sys.argv[1]
s = open(path).read()
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

M = "${KICAD10_3DMODEL_DIR}/"
b = pcbnew.LoadBoard(path)


def model(fp, name, offset, rotation):
    fp.Models().clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = M + name
    m.m_Offset = pcbnew.VECTOR3D(*offset)
    m.m_Rotation = pcbnew.VECTOR3D(*rotation)
    fp.Models().push_back(m)


for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref == "X1":     # contacts toward +y, tails at y 12.26 like the board's part
        model(fp, "Connector_FFC-FPC.3dshapes/Hirose_FH12-18S-0.5SH_1x18-1MP_P0.50mm_Horizontal.step",
              (0, -0.154, 0), (0, 0, 0))
    elif ref in ("JP1", "JP2"):     # flipped under the board, long pins down
        model(fp, "Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x09_P2.54mm_Vertical.step",
              (-10.16, 0, -1.6), (180, 0, 90))
b.Save(path)
EOF
"$CLI" pcb export step -f --include-tracks --include-pads --include-zones --include-silkscreen \
    --include-soldermask --user-origin=0x0mm -o "$HERE/5613 EYESPI Breakout.step" \
    $W/eyespi.kicad_pcb > /dev/null
rm -rf $W
echo "wrote $HERE/5613 EYESPI Breakout.step"
