# Printing the eink-audio-player stand

Eight STL files make the stand: nine printed pieces, since there are two cheeks. Each file
is one watertight solid (checked in FreeCAD: no non-manifold edges). The sizes below are
for each part in the orientation it should print in.

## Settings

- Printer: 0.4 mm nozzle, 0.2 mm layers.
- Walls: 4 perimeters (1.6 mm). This matches the design's minimum wall. Three walls
  (1.2 mm) is thinner than the design allows.
- Infill: 20%. The parts are thin bars, so most of the strength comes from the walls.
- Material: PLA works. PETG is tougher for the joint bosses and the screw pilots.
- Bed: all nine pieces fit a 180 x 180 mm bed. The largest is a cheek at 91 x 101.8 mm.
- Brim: the deck touches the bed on a small patch (about 1.2 cm2). Add a 5 mm brim.
- Supports: the bezel and deck have some overhang. The brace_top rod needs supports under
  its lower half when it lies down (see its row).

## Parts

| part | qty | size in print orientation (mm) | volume (cm3) | PLA grams (max) | orientation | notes |
|---|---|---|---|---|---|---|
| [bezel](../enclosure/stl/bezel.stl) | 1 | 79.0 x 82.0 x 18.4 | 15.67 | 19.4 | front face down | about 390 mm2 of overhang under the chin and bosses. Supports optional. |
| [deck](../enclosure/stl/deck.stl) | 1 | 79.0 x 7.2 x 28.8 | 3.06 | 3.8 | standing on back edge | 14.1 mm key holes bridge across the plate. About 410 mm2 of overhang. Use a brim. |
| [cheek_L](../enclosure/stl/cheek_L.stl) | 1 | 91.0 x 101.8 x 4.0 | 8.46 | 10.5 | outer face down | 2.8 mm clear holes and 4.8 mm counterbores open on the bed face. |
| [cheek_R](../enclosure/stl/cheek_R.stl) | 1 | 91.0 x 101.8 x 4.0 | 8.46 | 10.5 | outer face down | mirror of cheek_L. |
| [brace_front](../enclosure/stl/brace_front.stl) | 1 | 79.0 x 6.0 x 10.0 | 4.69 | 5.8 | flat on the desk face | print as built. Almost no overhang. |
| [brace_rear](../enclosure/stl/brace_rear.stl) | 1 | 79.0 x 6.0 x 10.0 | 4.69 | 5.8 | flat on the desk face | same as brace_front. |
| [brace_top](../enclosure/stl/brace_top.stl) | 1 | 79.0 x 7.0 x 7.0 | 2.99 | 3.7 | lying down | about 380 mm2 of overhang under the lower half. Use supports, or print it upright. |
| [battery_strap](../enclosure/stl/battery_strap.stl) | 1 | 79.0 x 22.5 x 9.0 | 1.67 | 2.1 | stile face down | no overhang. |

Grams are an upper bound: 100% solid PLA at 1.24 g/cm3. A printed part with walls and
20% infill uses less. Total for all nine pieces: 49.7 cm3, at most 61.6 g.

## Assembly

Use M2.5 screws throughout. The pilots are 2.2 mm, sized for self-tapping M2.5 screws.

1. Deck and NeoKey. Set the NeoKey on the four deck standoffs and screw it down.
2. Bezel and display. Put the display on the bezel. Run the four longer M2.5 display
   screws through the bezel bosses, the display, the board and into the brass standoffs.
3. Battery strap. Set the LiPo under the strap. Drive one M2.5 screw from behind into
   each bezel stile.
4. Cheeks and joints. Fit the two cheeks to the bezel and deck bosses. Screw through the
   2.8 mm holes on the outer face into the boss pilots.
5. Braces. Fit brace_front and brace_rear to the feet, and brace_top to the top rear
   joints.
6. STEMMA QT cable. Route the cable from the Feather to the NeoKey QT connector before
   the last screws go in.
7. Joint screws. Put in all 14 joint screws: four on the bezel, four on the deck, four
   on the feet and two at the top rear.

Total M2.5 count: 4 display screws, 2 battery strap screws, 4 NeoKey screws and 14 joint
screws, 24 in all.
