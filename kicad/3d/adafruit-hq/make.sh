#!/bin/zsh
# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Rebuild the high-detail Adafruit board models in kicad/3d/. Each Adafruit_CAD_Parts STEP
# has coloured parts on a plain tan "Board" body; that body is swapped for Adafruit's own
# Eagle board imported into KiCad (black mask, white silkscreen, ENIG pads), in the same
# frame, so the footprints' model offsets stay right.
#
#   python3 -m venv ~/ocp && ~/ocp/bin/pip install cadquery-ocp   # OCCT for merge.py
#   PY=~/ocp/bin/python ./make.sh
#
# Copper pours and traces are left out: they sit under the opaque mask and would triple
# the file size.
set -e
HERE=${0:A:h}; OUT=${HERE:h}
PY=${PY:-python3}
CLI=${CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
KP=${KP:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
W=$(mktemp -d)
GH=https://raw.githubusercontent.com/adafruit
CAD=$GH/Adafruit_CAD_Parts/main

# name | output (and Adafruit_CAD_Parts folder/file) | Eagle board
BOARDS=(
  "feather|6000 Feather RP2350|Adafruit-Feather-RP2350-PCB/HEAD/Adafruit Feather RP2350.brd"
  "tlv|6309 TLV320DAC3100 I2S DAC|Adafruit-TLV320DAC3100-I2S-DAC-PCB/HEAD/Adafruit TLV320DAC3100 I2S DAC.brd"
  "neokey|4980 NeoKey 1x4 QT|Adafruit-NeoKey-1x4-PCB/HEAD/Adafruit NeoKey 1x4 QT I2C.brd"
  "eink|6366 2.13in Tri-Color eInk|Adafruit-E-Paper-Display-Breakout-PCBs/HEAD/Adafruit 2.13in Tri-Color eInk with EYESPI.brd"
  "ano|5740 ANO Rotary Encoder QT|Adafruit-ANO-Rotary-Navigation-Encoder-to-I2C/HEAD/Adafruit ANO Rotary Encoder to I2C.brd"
)
for row in $BOARDS; do
  n=${row%%|*}; rest=${row#*|}; name=${rest%%|*}; brd=${rest#*|}
  curl -sfL -o $W/$n.brd "$GH/${brd// /%20}"
  curl -sfL -o "$W/$n-ada.step" "$CAD/${name// /%20}/${name// /%20}.step"
  "$CLI" pcb import --format eagle -o $W/$n.kicad_pcb $W/$n.brd > /dev/null
  "$KP" $HERE/prep.py $W/$n.kicad_pcb 2>&1 | grep edges || true
  "$CLI" pcb export step -f --board-only --include-pads --include-silkscreen --include-soldermask \
      --user-origin=0x0mm -o $W/$n-board.step $W/$n.kicad_pcb > /dev/null
  $PY $HERE/merge.py "$W/$n-ada.step" $W/$n-board.step "$OUT/$name.step"
done
rm -rf $W
