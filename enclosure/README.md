# eink-audio-player stand

The stand is a skeleton, not a box. Two side frames (cheeks) hold the e-ink screen tilted
back at 65 degrees and the key deck in front at 10 degrees, and cross braces tie the
cheeks together on the desk. The bezel frames the e-ink display and carries the board
stack on four M2.5 screws. The deck is the MX switch plate for the NeoKey, and the
battery strap is a ladder across the LiPo's lower half. Every joint is one M2.5
self-tapping screw driven into a 2.2 mm pilot, along X at x = ±39.5 mm. The USB-C port,
headphone jack and SW1 knob stay clear, and the STEMMA QT cable from the Feather runs to
the NeoKey through an open path at the back. All parts are built in one shared frame
(`layout.py` writes `layout.json`), checked against the real board models, and checked
against each other by `assemble_arcade.py`.

| Part | What it does | Print orientation | Volume (cm³) |
|---|---|---|---|
| `bezel` | Frame over the e-ink, two stiles down to the cheeks, chin under the board edge the stack rests on | Front face down | 15.67 |
| `deck` | MX switch plate over the NeoKey, four standoffs, front rib, end bosses to the cheeks | On its back edge | 3.06 |
| `cheek_L` | Left side frame: arcade profile, clear holes and counterbores at each joint | Flat on outer face | 8.46 |
| `cheek_R` | Right side frame, mirror of `cheek_L` about X = 0 | Flat on outer face | 8.46 |
| `brace_front` | Front foot bar tying the cheeks on the desk | Flat | 4.69 |
| `brace_rear` | Rear foot bar tying the cheeks on the desk | Flat | 4.69 |
| `brace_top` | Round top bar across the cheeks, doubles as a carry handle | On its end or lying down | 3.00 |
| `battery_strap` | Ladder over the LiPo, two tabs against the slope, end plates on the bezel stiles | Stile face down | 1.67 |

Volumes are the solid volumes from `assemble_arcade.py` (FreeCAD, one solid per part).
