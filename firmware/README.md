# Firmware

`code.py` is a FLAC player for the board. It plays every `.flac` file in one folder on the microSD card, in name order, through the TLV320DAC3100 to the headphone jack. Tested on CircuitPython 11.0.0-alpha.2 on the Feather RP2350.

## Before you start: the MCLK jumper

Solder a wire from **TP1** (Feather D5) to **TP2** (TLV320 MCLK). Both are large pads labelled `JMP` on the board. TP2 sits under the TLV320 breakout, so solder the wire before you plug the breakout in.

D5 sends a 15 MHz clock to the TLV320's MCLK pin. The TLV320's PLL locks to it. Without the jumper, the PLL has to run from the I2S bit clock, and the audio sounds muffled.

## Pins

| Function | Feather pin |
|---|---|
| I2S BCLK | A0 |
| I2S WSEL | A1 |
| I2S DIN | A2 |
| TLV320 MCLK (15 MHz PWM, over the jumper) | D5 |
| TLV320 control (I2C) | SCL, SDA |
| microSD (on the EYESPI breakout) | SCK, MOSI, MISO, CS on D24 |

## Setup

1. Install the libraries: `circup install adafruit_flac adafruit_tlv320`
2. Copy `code.py` to the CIRCUITPY drive.
3. Set `ALBUM` at the top of `code.py` to a folder on your card, for example `"/Shpongle-Tales_Of_The_Inexpressible-2001"`.

The card is read through the `VfsFat` object directly, so CIRCUITPY needs no `/sd` folder.

## Settings

| Setting | Default | What it does |
|---|---|---|
| `ALBUM` | a folder on the card | Folder to play |
| `LEVEL` | 0.5 | Output level, 0.0 to 1.0 |
| `DAC_DB` | -16 | TLV320 DAC volume in dB |
| `BUFFER_MS` | 100 | Length of each half of the output buffer |

## Performance

16-bit/44.1 kHz FLAC, read from the card at 24 MHz:

| Measure | Result |
|---|---|
| Decode load | 35 to 41% of real time |
| Slowest frame decode | 63 ms |
| Underruns, 8 minute track | 0 |

The default 64 ms buffer half is too tight, because one frame can take 63 ms to decode, so `code.py` uses 100 ms.

## Gotcha: reserve the I2S buffers first

The I2S DMA buffers come from a small internal-RAM heap. If the FLAC decoder and the SD driver load first, `FLACPlayer.play` fails with `RuntimeError: Unable to allocate buffers for signed conversion`. `code.py` creates the `I2SOut` and plays the empty output buffer once, before any other imports, so those buffers are reserved early.
