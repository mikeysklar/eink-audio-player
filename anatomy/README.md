# Anatomy build

The interactive isometric "anatomy" figure of the player, built from `pcb.json` (KiCad board dump) and `solids.json` (STEP solid bounds). It is posed as on the stand, from `enclosure/layout.json`: the board at 65 degrees seen from behind, with the keys and the ANO in front.

- Needs the Anatomy kit (`kit/iso-kit.mjs`). Set `ANATOMY_DIR` to the `anatomy-skill` folder; without it, the old local path is used only if it exists.
- Rebuild the solid list: `freecadcmd anatomy/solids.py` reads `enclosure/inputs/board.step` (run from any folder; it writes `solids.json` to the current folder, so run it in `anatomy/`).
- Rebuild the PCB dump: `python3 anatomy/dump_pcb.py <board.kicad_pcb> anatomy/pcb.json`.
- Build the page: `ANATOMY_DIR=/path/to/anatomy-skill node anatomy/build.mjs --light` writes `out/frisson-light.html`.
- Hero variant for recording: `node anatomy/build.mjs --light --hero` writes `out/frisson-hero-light.html` (no hint text).
- `record.mjs` is not in the repo or the kit yet, so the GIF and MP4 step is still manual.
