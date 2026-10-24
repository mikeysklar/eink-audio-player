# eink-audio-player hardware

Parts, pin map and stand hardware for the eink-audio-player. Counts come from the
landing pad PCB (`landing-pad.kicad_pcb`), the netlist as routed on the board, and the
stand scripts in `arcade/`.

## Parts list

### Adafruit boards and parts

| Part | Adafruit PID | Link |
|---|---|---|
| Feather RP2350 | 6000 | [product/6000](https://www.adafruit.com/product/6000) |
| TLV320DAC3100 I2S DAC breakout | 6309 | [product/6309](https://www.adafruit.com/product/6309) |
| 2.13" quad-colour e-ink display | 6366 | [product/6366](https://www.adafruit.com/product/6366) |
| EYESPI breakout | 5613 | [product/5613](https://www.adafruit.com/product/5613) |
| NeoKey 1x4 QT | 4980 | [product/4980](https://www.adafruit.com/product/4980) |
| LiPo battery, 2000 mAh | 2011 | [product/2011](https://www.adafruit.com/product/2011) |
| STEMMA QT cable, 200 mm (JST SH to JST SH) | 4401 | [product/4401](https://www.adafruit.com/product/4401) |
| ANO rotary encoder, I2C, encoder fitted (thumb control) | 6310 | [product/6310](https://www.adafruit.com/product/6310) |
| STEMMA QT cable, 100 mm (NeoKey to ANO) | 4210 | [product/4210](https://www.adafruit.com/product/4210) |
| microSD card | any | no PID |
| Cherry MX compatible key switches, x4 | any | no PID |
| Keycaps for the four switches | any | no PID |

Cable choice: the 200 mm cable (PID 4401). The Feather's QT port (`feather_qt` in
`arcade/layout.json`, at x 6.8 mm) to the NeoKey QT port on the near side (x 35.6 mm,
`neokey_qt`) is 77 mm in a straight line. The far NeoKey port is 83 mm away. A 100 mm
cable has no room for the run along the stand, so 200 mm leaves slack.

The ANO chains off the NeoKey's other QT port. That port (x 35.6 mm) faces the right
cheek, and the plug passes through the cheek's window; the ANO's own port faces back
toward the stand, about 35 mm away in a straight line. A 100 mm cable (PID 4210) covers
the bend round the cheek. The ANO is at I2C address 0x49, clear of the NeoKey (0x30) and
the TLV320 (0x18).

Each board needs headers that match the sockets. The landing pad uses female sockets, so
the boards take male header pins.

### Landing pad PCB parts

Counted from the footprints on `landing-pad.kicad_pcb`:

| Part | Count | Footprint | Ref |
|---|---|---|---|
| SMD female socket, 16 pin (Feather JP1) | 1 | PinSocket_1x16 P2.54 SMD | J1 |
| SMD female socket, 12 pin (Feather JP3) | 1 | PinSocket_1x12 P2.54 SMD | J2 |
| SMD female socket, 9 pin (EYESPI 1-9) | 1 | PinSocket_1x09 P2.54 SMD | J4 |
| SMD female socket, 9 pin (EYESPI 10-18) | 1 | PinSocket_1x09 P2.54 SMD | J5 |
| SMD female socket, 10 pin (TLV JP3) | 1 | PinSocket_1x10 P2.54 SMD | J9 |
| SMD female socket, 8 pin (TLV JP1) | 1 | PinSocket_1x08 P2.54 SMD | J10 |
| 0805 0R jumper | 4 | R_0805_2012Metric | R1, R2, R3, R4 |
| Slide switch, MSK-12C03 (power) | 1 | SW_SPDT_MSK-12C03 | SW1 |

Totals: 6 socket strips (64 pins), 4 jumpers, 1 slide switch. The PCB has no other
resistors, capacitors or ICs. The seven M2.5 mounting holes (H1-H7, 2.7 mm, unplated)
need no parts.

## Pin map

Feather pins are the header pads on the landing pad sockets. GPIO numbers are from the
Feather RP2350 pin list. "Via" lists the 0R jumper on the way.

### Feather JP1 (socket J1, 16 pin)

| Feather pin | CircuitPython | GPIO | Net | Goes to |
|---|---|---|---|---|
| 2 | `board.TX` | GPIO0 | EPD_RST | EYESPI pin 8, RST |
| 3 | `board.RX` | GPIO1 | EPD_DC | EYESPI pin 7, DC |
| 4 | `board.MISO` | GPIO20 | MISO | EYESPI pin 6, MISO |
| 5 | `board.MOSI` | GPIO23 | MOSI | EYESPI pin 5, MOSI |
| 6 | `board.SCK` | GPIO22 | SCK | EYESPI pin 4, SCK |
| 7 | `board.D25` | GPIO25 | EPD_TCS | EYESPI pin 9, TCS |
| 8 | `board.D24` | GPIO24 | SD_CS | EYESPI pin 10, SDCS |
| 9 | `board.A3` | GPIO29 | EPD_BUSY | EYESPI pin 16, BUSY |
| 10 | `board.A2` | GPIO28 | I2S_DIN | via R1, TLV pin 5 (DIN) |
| 11 | `board.A1` | GPIO27 | I2S_WSEL | via R2, TLV pin 6 (WSEL) |
| 12 | `board.A0` | GPIO26 | I2S_BCLK | via R3, TLV pin 7 (BCLK) |
| 14 | 3V3 | n/a | 3V3 | TLV pin 1, EYESPI pin 1 (VIN) |
| 13 | GND | n/a | GND | TLV pin 2, SW1 pin 3, EYESPI pin 3 via R4 |

Feather pins 1, 15 and 16 are left open (PSRAM_CS, the second 3.3 V pad, RESET).

### Feather JP3 (socket J2, 12 pin)

| Feather pin | CircuitPython | GPIO | Net | Goes to |
|---|---|---|---|---|
| 2 | `EN` | n/a | EN | SW1 pin 2 (power slide switch) |
| 11 | `board.SCL` | GPIO3 | SCL | TLV pin 3 (SCL) |
| 12 | `board.SDA` | GPIO2 | SDA | TLV pin 4 (SDA) |

Feather pins 1, 3 to 10 are open (VBAT, VBUS, D13, D12, D11, D10, D9, D6, D5).

### Notes on the pin map

- The SPI bus is the Feather's `board.SCK`, `board.MOSI` and `board.MISO`, which go to
  the EYESPI breakout. The display and microSD share it, with separate chip selects.
- The I2S lines sit on A0, A1 and A2 (GPIO26, 27, 28). BCLK and WSEL must be consecutive
  GPIOs for RP2xxx PIO I2S, and they are.
- EYESPI pin 3 (GND) reaches ground through the R4 jumper, not directly.
- The NeoKey and its key switches do not use landing pad pins. They hang off the
  Feather's STEMMA QT port (SDA and SCL, through the 200 mm cable). The ANO hangs off
  the NeoKey's second QT port.

## Stand hardware

The stand is a mini arcade: the screen tilts back, and the keys sit on their own deck in
front. The parts are joined by M2.5 screws.

### Joints (cheeks)

There are 14 joints, one M2.5 per joint, from the outside of each 4 mm cheek into a
6 mm pilot in the owning part. Each cheek has a 2.8 mm clear hole and a 4.8 mm
counterbore, 1.5 mm deep, on the outside. Each joint has 2.5 mm of cheek left after the
counterbore, then the 6 mm pilot.

| Joint | Count | Screw |
|---|---|---|
| bezel top, bezel bottom (left and right) | 4 | M2.5 x 10 mm |
| deck back, deck front (left) | 2 | M2.5 x 10 mm |
| deck back, deck front (right, through the ANO mount arm) | 2 | M2.5 x 12 mm |
| foot front, foot rear (left and right) | 4 | M2.5 x 10 mm |
| top rear (left and right) | 2 | M2.5 x 10 mm |

The 10 mm length puts about 7.5 mm of thread into the 6 mm pilot. It leaves a tip
about 1.5 mm past the pilot bottom. Keep the head height at or below 1.5 mm so it sits in
the counterbore.

### Display (through the bezel into brass standoffs)

| Part | Count | Length |
|---|---|---|
| M2.5 screw, bezel to display to standoff | 4 | 8 mm |
| M2.5 screw, landing pad through H1 to H4 into standoff bottom | 4 | 6 mm |
| Brass standoff, M2.5, between display PCB and board | 4 | 9.5 mm |

Measured stack, from the front of the bezel: head seat 2.0 mm deep in the bezel
counterbore, bezel 2.2 mm to the back, 0.05 mm gap, display PCB 1.57 mm, then the
standoff. The screw has about 3.8 mm to the standoff top, which leaves about 4 mm of
thread in the standoff with an 8 mm screw. The standoff spans the 9.5 mm from the display
PCB back to the board's bottom face. The four holes sit on the board corners at
x 2.6 and 58.5 mm, y 39.3 and 73.6 mm (H1 to H4), away from the battery.

The board is fixed to the standoff bottoms by 4 more M2.5 x 6 mm screws, from the landing
pad side through H1 to H4 into the standoffs.

### Battery straps

| Part | Count | Screw |
|---|---|---|
| Battery strap end plate, to bezel stile | 2 | M2.5 x 6 mm |

The strap plate is 1.7 mm thick. The pilot in the stile is 5 mm of stile from its back
face. A 6 mm screw gives about 4 mm of thread in the stile, and its tip stays inside the
stile.

### ANO mount

| Part | Count | Screw |
|---|---|---|
| M2.5 screw, ANO board into the mount's standoffs | 4 | 6 mm |

The mount's arm sits on the outside of the right cheek and takes the two right deck
joints: 2.0 mm counterbore in the 4 mm arm, the 4 mm cheek, then the 6 mm pilot in the
deck boss, so those two are 12 mm. The ANO's 1.6 mm board sits on four printed standoffs
with 5.5 mm pilots, so a 6 mm screw gives about 4.4 mm of thread.

### Keys (NeoKey into deck standoffs)

| Part | Count | Screw |
|---|---|---|
| M2.5 screw, deck plate to standoff to NeoKey | 4 | 6 mm |

The stack is the 1.6 mm NeoKey PCB, the 3.5 mm standoff (4.4 mm of it used by the screw)
and the 1.5 mm deck plate. The pilot runs through to the plate top, so a 6 mm screw seats
fully. The standoffs are printed on the deck, so they need no hardware.

## Screw total

| Length | Count | Used for |
|---|---|---|
| M2.5 x 6 mm | 14 | 2 battery strap, 4 NeoKey, 4 board to standoff, 4 ANO |
| M2.5 x 8 mm | 4 | display, bezel to standoff |
| M2.5 x 10 mm | 12 | cheek joints |
| M2.5 x 12 mm | 2 | right deck joints, through the ANO mount arm |
| **Total** | **32** | |

Also needed: 4 brass M2.5 standoffs, 9.5 mm (display).
