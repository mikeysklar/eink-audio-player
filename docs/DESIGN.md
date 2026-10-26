# Frisson design notes

Short notes on how the board and the stand are built. The numbers come from the build scripts.

## Board

The Feather, the TLV320DAC3100 DAC, the EYESPI breakout and the display's flex all plug into one PCB, the landing pad. The 2000 mAh LiPo and the display sit behind it.

- Sockets: the Feather uses J1 (16-pin) and J2 (12-pin). The TLV uses J9 and J10. The EYESPI breakout uses J4 and J5. All are stock SMD female sockets.
- Single-sided and milled: top copper only, no vias. Every trace is on F.Cu.
- The GND fill is the only copper pour. It is solid onto GND pads, with no thermals.
- Traces are 0.4 mm, and the gaps are 0.4 mm. The 3V3 lane is 0.4 mm too, since the board draws about 150 mA at most.
- The fill keeps 0.1 mm from the board edge and from every screw hole. Other copper keeps 0.5 mm from the edge and 0.4 mm from the holes.
- The fill must run unbroken round the whole board, with no cut-off sections near the edge. Gaps there cause problems when the files are exported to the laser. Status pane check: "fill 0.1 to edge + holes: ring closed".

### Design rules

The KiCad project's custom rule file holds these rules, and KiCad checks them on every DRC run.

| Rule | Value |
| --- | --- |
| Copper to 0805 jumper pads | 0.2 mm |
| Copper to a screw head | 1.0 mm |
| Fill to a screw head | 0.1 mm |
| Other copper to a screw hole | 0.4 mm |
| Copper to the board edge | 0.5 mm |

The jumper rule exists because an 0805's pads sit 0.8 mm apart. A 0.4 mm trace under one keeps 0.2 mm to each pad.

### Jumpers

- R1 to R4 are 0R 0805 jumpers. They are the only way a trace crosses another on one copper layer.
- The first pass had 8 jumpers. The routing now needs 4.
- R4 joins two pieces of the GND fill. KiCad cannot see through a 0R, so each piece that a track cuts off is its own net.

### Signals

- Display: SCK, MOSI and MISO go from J1 to the EYESPI breakout. The five control lines (busy, SD chip select, touch chip select, RST, DC) come off the Feather's other pins.
- Music: the MP3s live on the microSD slot on the display's EYESPI breakout. It shares the SPI bus, and its chip select is EYESPI pin 10 (SDCS), which lands on the Feather's D24.
- I2S: BCLK is on A0, WSEL is on A1 and DIN is on A2. These are three consecutive pins, as the PIO I2S needs. The same pins are used on the i2s-amp-shim.
- MCLK is not wired. The TLV's PLL runs from BCLK.
- TLV RST is not wired. Pin 5 of J10 is open, and a 10K pull-up on the TLV breakout holds it high.
- Keys: the NeoKey 1x4 is on STEMMA QT, so it needs no pins on the board.

### Parts on the back

- The LiPo sits centred on the back, 8 mm in from the top and bottom edges.
- The display is flush with the top edge. Its flex wraps off the EYESPI breakout over the top edge, so the fold is short.
- The NeoKey 1x4 sits centred below the display. Its hot-swap sockets sit on the battery.
- The power switch (SW1, a side slide) sits on the board edge, 11 mm down from the top.
- Seven M2.5 holes, H1 to H7. Four hold the display. H5 is the Feather's corner, H6 the TLV's corner and H7 is bare bottom-left. The battery clears all of them.

### Checks

From the status pane, last recorded:

- Plan checker: 0 errors, 0 open routes.
- DRC: 0 errors. Parity: 0. ERC: 0.

## Stand

The stand is a skeleton. It has no walls. The screen and the keys sit on two separate bodies.

- Desk is Z=0. The player sits at -Y and looks toward +Y. X is the player's right, and the stand is symmetric about X=0.
- The stack is the board with the Feather, DAC, EYESPI, battery and display. It is tilted 65 degrees from the desk, with the board's top edge (the flex fold) highest.
- The keys are the NeoKey 1x4 on their own deck in front, keys up, tilted 10 degrees from the desk.
- One STEMMA QT cable joins the two.
- Ports face the player's left. The USB-C, the headphone jack and SW1 all sit on the board's right edge, and their keep-out circles run along -X. These are 14 mm, 11 mm and 9 mm across.

### Chassis and joints

- The chassis is one print: two cheeks, 4 mm thick, with inner faces at x = +-39.5, the front and rear foot bars, and the ANO mount.
- Everything between the cheeks stops 0.25 mm short of each inner face.
- The bezel and the deck each have four bosses, 6.0 mm across, at the layout joints. On each part, one pair of bosses takes heat inserts (3.3 mm holes, 3.3 mm deep), and the other pair has 4.0 mm pegs, 1.2 mm long.
- The pegs sit in slots on the cheeks' inner faces, 4.4 mm wide and 1.5 mm deep. The bezel's slots open toward the player, the way the bezel slides in. The deck's open straight up, the way the deck drops in.
- At the insert bosses, each cheek has a 2.8 mm clear hole and a 4.8 x 1.5 mm counterbore on its outer face, for an M2.5 x 8.
- The handle pushes through a 7.4 mm hole in the left cheek and snaps into a 4.0 mm hole in the right one.

### Parts

- Bezel: a frame over the display, two stiles down the sides, and a chin under the board's bottom edge. Four M2.5 x 16 from the board side clamp the board, the cradle and the display to it, into inserts in its back.
- Cradle: four 6 mm posts that span the 9.5 mm between the display and the board at H1 to H4, side rails, and two bars across the LiPo's lower half with two tabs that stop it sliding down the slope. It replaces the brass standoffs and the battery strap. The rails lift over the two parts on the display's back.
- Deck: the MX switch plate, 5.0 mm above the NeoKey face, with four standoffs and a front rib. Two standoffs take inserts and two carry pins into the NeoKey's holes. Its back bosses sit under the bezel chin, which keeps them down. The MX spec hole is 14.0 mm. The deck prints it at 14.1 mm to allow for FDM holes printing small.
- Handle: a 7 mm rod with a flange on the left and a split, barbed snap on the right.
- ANO mount, part of the chassis: holds the ANO rotary encoder (6310) for the thumb, past the right end of the keys and toward the player, at the keys' 10 degrees. The wheel centre is 35 mm right of the last key and 39 mm closer, and sits 12 mm below the keycap tops. An arm joins it to the right cheek's outer face, with an open bore over the right front deck screw. Four standoffs carry the ANO, two with inserts and two with pins, and the front rail runs to the desk so a press does not lever the stand. The ANO's STEMMA QT port faces the stand, so the cable from the NeoKey's right port runs through the cheek window.
- Min wall is 1.6 mm, for printing with a 0.4 mm nozzle, and 1.1 mm round the inserts in the bosses and standoffs. The two top display inserts in the bezel sit 0.5 mm from the glass pocket. Clearance to the real parts is 0.3 mm or more.

### Checks in assemble_arcade.py

The script writes `arcade.FCStd` and `arcade.step`, and it prints a PASS or FAIL for each check:

- Each part is one valid solid.
- Each part clashes with the stack and the keys by under 0.01 mm3. These are the real board models.
- No two parts overlap by more than 0.01 mm3.
- The 12 screws and 12 inserts (`fasteners.py`) touch nothing: heads at full size, shanks and inserts at their holes' cores.
- Each part's way in, run backwards in 2 mm steps, hits nothing already in place: the bezel with the stack out to the front, the deck with the keys straight up, the handle out to the left, and the ANO up off its standoffs.
