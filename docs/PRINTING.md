# Printing the eink-audio-player stand

Five STL files make the stand, one printed piece each. Each file is one watertight solid
(checked in FreeCAD). The sizes below are for each part in the orientation it should
print in.

## Settings

- Printer: 0.4 mm nozzle, 0.2 mm layers.
- Walls: 4 perimeters (1.6 mm). This matches the design's minimum wall. Three walls
  (1.2 mm) is thinner than the design allows.
- Infill: 20%. The parts are thin bars, so most of the strength comes from the walls.
- Material: PLA works. PETG is tougher for the handle's snap.
- Bed: all five pieces fit a 180 x 180 mm bed. The largest is the chassis at
  128 x 141 mm.
- Supports: tree supports for the chassis (see its row). The others need little or none.

## Parts

| part | qty | size in print orientation (mm) | volume (cm3) | PLA grams (max) | orientation | notes |
|---|---|---|---|---|---|---|
| [chassis](../enclosure/stl/chassis.stl) | 1 | 128.1 x 140.5 x 91.0 | 30.38 | 37.7 | upright, on its feet | both cheeks, the foot bars and the ANO mount in one piece. Tree supports under the roof, waist and deck rails and the tilted ANO frame. |
| [bezel](../enclosure/stl/bezel.stl) | 1 | 80.9 x 82.0 x 18.4 | 15.72 | 19.5 | front face down | some overhang under the chin and bosses. Supports optional. |
| [deck](../enclosure/stl/deck.stl) | 1 | 80.9 x 8.7 x 28.8 | 3.15 | 3.9 | standing on its back edge | 14.1 mm key holes bridge across the plate. Use a 5 mm brim. |
| [cradle](../enclosure/stl/cradle.stl) | 1 | 61.9 x 70.1 x 9.5 | 3.88 | 4.8 | display face down | the side rails bridge about 15 mm over two parts on the display's back. |
| [handle](../enclosure/stl/handle.stl) | 1 | 90.0 x 11.0 x 8.4 | 3.19 | 4.0 | lying on its flat | a small support under the snap pin, which stands 1 mm off the bed. |

Grams are an upper bound: 100% solid PLA at 1.24 g/cm3. A printed part with walls and
20% infill uses less. Total for all five pieces: 56.3 cm3, at most 69.8 g.

## Heat inserts

Twelve M2.5 brass heat inserts, 3.3 mm across and 3.3 mm long, go in once with a
soldering iron, at the temperature your inserts call for. The holes are 3.1 mm across
and 3.8 mm deep:

- bezel: 4 on the back face (the display screws) and 1 in each top boss end
- deck: 1 in each front boss end, and 2 in the standoffs on one diagonal
- chassis: 2 in the ANO standoffs on one diagonal

Press each one square and flush. A crooked insert makes the screw bind.

## Assembly

See [HARDWARE.md](HARDWARE.md) for the order and the screw lengths: 12 M2.5 socket head
screws in all, four each of 6, 8 and 16 mm.
