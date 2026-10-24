#!/bin/zsh
# Export the eink-audio-player board and each part to GLB for render.py.
# Same origin as case/build/board.step (board bbox bottom-left, Y up), so the
# arcade layout.json matrices place them directly.
#   ./export.sh [path/to/board.kicad_pcb]
set -e
PCB=${1:-/Volumes/clear/Downloads/ada/hstx-audio/landing-pad/landing-pad.kicad_pcb}
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
CAD=${0:A:h}/cad
ORIGIN=99.95x154.21mm
mkdir -p "$CAD"
glb() { "$CLI" pcb export glb "$PCB" -f -o "$CAD/$1.glb" --subst-models --no-dnp --user-origin=$ORIGIN "${@:2}" > /dev/null 2>&1; echo "wrote cad/$1.glb"; }

glb board --no-components --include-tracks --include-pads --include-zones
for ref in A1 A3 A5 A7 ANO1 BT1 DS1 J1 J2 J4 J5 J9 J10 SW1 R1 R2 R3 R4; do
    glb $ref --no-board-body --component-filter $ref
done
