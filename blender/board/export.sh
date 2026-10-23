#!/bin/zsh
# Export the board and each part group to GLB for turntable.py.
# Origin is the board bbox bottom-left, Y up. turntable.py recentres the board, so the origin
# only matters for reading the GLBs by hand.
#   SRC=/path/to/landing-pad OUT=/path/to/scratch/cad ./export.sh
set -e
SRC=${SRC:-/Volumes/clear/Downloads/ada/hstx-audio/landing-pad}
OUT=${OUT:-${0:A:h}/cad}
CLI=${CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
PCB=$SRC/landing-pad.kicad_pcb
ORIGIN=99.95x154.21mm
mkdir -p "$OUT"
glb() { "$CLI" pcb export glb "$PCB" -f -o "$OUT/$1.glb" --subst-models --user-origin=$ORIGIN "${@:2}" > /dev/null 2>&1; echo "wrote $OUT/$1.glb"; }

glb board --no-components --include-tracks --include-pads --include-zones
for ref in A1 A3 A7 J1 J2 J4 J5 J9 J10 SW1 R1 R2 R3 R4 BT1 DS1 A5; do
    glb $ref --no-board-body --component-filter $ref
done
