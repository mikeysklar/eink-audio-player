# Blender renders

Turntable and break-apart animations of the eink-audio-player: the printed mini arcade stand
with every board in place. Output goes to `docs/media/blender/`.

| File | What |
|---|---|
| `export.sh` | `kicad-cli pcb export glb`: the bare board and one GLB per part into `cad/` |
| `cad/*.glb` | Board frame, same origin as `case/build/board.step` (`--user-origin=99.95x154.21mm`) |
| `render.py` | Builds the scene, keys the turntable or the explode, renders stills |
| `render.sh` | Renders a `.blend` with 3 Blender processes on the Metal GPU, then encodes the MP4 |
| `turntable.blend`, `explode.blend` | Scenes saved by `render.py`, input to `render.sh` |

## Run

```sh
cd blender
./export.sh                                                      # ~20 s
blender -b --factory-startup --python render.py -- check         # EEVEE check stills
blender -b --factory-startup --python render.py -- hero          # Cycles hero.png, exploded.png
blender -b --factory-startup --python render.py -- turntable     # writes turntable.blend
blender -b --factory-startup --python render.py -- explode       # writes explode.blend
./render.sh turntable.blend ../docs/media/blender/turntable.mp4
./render.sh explode.blend ../docs/media/blender/explode.mp4
```

GIFs (640 px, ffmpeg palette):

```sh
ffmpeg -i turntable.mp4 -vf "fps=15,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" turntable.gif
```

## How the parts are placed

Everything is in the stand's world frame from `arcade/layout.py`: mm, desk at Z=0, Z up, the
player at -Y. The printed parts are `arcade/build/*.stl`, already in that frame. The boards are
two rigid bodies placed with the matrices in `arcade/layout.json`: `stack` (carrier board, Feather,
TLV320DAC3100, EYESPI, LiPo, e-ink) and `keys` (NeoKey 1x4 with its MX switches and keycaps).
A board point p goes to `p0 + p.x*bx + p.y*by + p.z*bz`. The glTF importer already turns the
GLB's Y-up metres into Blender Z-up, so an imported point in mm is p.

Placed bounding boxes match `arcade/build/keys.step` exactly and `stack.step` to within 0.4 mm
(the EYESPI model reaches Y=55.6 here, 55.19 in stack.step).

## Look

Cycles on the Metal GPU, 64 samples with denoising, AgX Punchy. Printed parts are matte PLA in
the `assemble_arcade.py` colours, with a faint 0.2 mm layer line bump. Board colours follow the
earlier turntable: black mask with ENIG on the Adafruit breakouts, bare milled FR4 and copper on
the carrier, paper white e-ink. Softboxes ride on the camera rig, so every side is lit the same.

## Explode timeline (8 s)

Hold, then the cheeks slide sideways, the top bar lifts, the floor braces slide out, the bezel
flies forward and up, the board stack rises out of the stand and spreads (e-ink and battery
toward the player, breakouts back), the NeoKey lifts off its deck. Hold, then it all closes up.
The camera dollies out and back and sways 14 degrees, so the clip loops cleanly. Offsets and
times are `MOVES` at the top of `render.py`.
