# eink-audio-player stand

The stand is a skeleton, not a box, in five printed parts. The red chassis is both side
frames (cheeks), the two foot bars and the ANO mount in one piece. It holds the e-ink
screen tilted back at 65 degrees and the key deck in front at 10 degrees. The bezel
frames the e-ink display and carries the board stack, clamped through the cradle by four
M2.5 x 16 screws. The bezel slides in from the front and the deck drops in from above.
Pegs locate each one in slots in the cheeks, and two M2.5 x 8 screws hold each. Every
screw goes into a brass heat insert: 12 screws in all (`parts/fasteners.py` places them).
The handle snaps in with no screws. The USB-C port, headphone jack and SW1 knob stay
clear, and the STEMMA QT cables run through windows in the cheeks. All parts are built in
one shared frame (`layout.py` writes `layout.json`) and checked against the real board
models, against each other, and along the way each one goes in, by `assemble_arcade.py`.

| Part | What it does | Print orientation | Volume (cm³) |
|---|---|---|---|
| `chassis` | Both cheeks, the front and rear foot bars, and the ANO mount (6310) past the right end of the keys. Slots for the bezel and deck pegs, counterbored holes for their screws, holes for the handle | Upright, tree supports | 30.38 |
| `bezel` | Frame over the e-ink, two stiles down to the cheeks, chin under the board edge. Inserts for the stack and the top screws, pegs at the bottom | Front face down | 15.72 |
| `deck` | MX switch plate over the NeoKey, two insert standoffs and two pins, front rib, pegs at the back, inserts at the front | On its back edge | 3.15 |
| `cradle` | Four posts between the display and the board, rails, and the bars and tabs that hold the LiPo | Display face down | 3.88 |
| `handle` | Round top bar and carry handle: pushes through the left cheek, snaps into the right | Lying on its flat | 3.19 |

Volumes are the solid volumes from `assemble_arcade.py` (FreeCAD, one solid per part).
