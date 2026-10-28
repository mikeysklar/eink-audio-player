# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""FLAC player for the Frisson board.

Plays the .flac files on the microSD card through the TLV320DAC3100 to the
headphone jack, with menus on the e-ink screen. lib/menus.py lists what every
key does: browse with the ANO wheel, and the NeoKeys are play / pause /
reverse / forward.

Board (see kicad/):
  - I2S on A0 BCLK, A1 WSEL, A2 DIN.
  - The TLV's MCLK comes from D5 over the TP1-TP2 jumper wire. D5 runs a
    15 MHz PWM clock and the TLV's PLL locks to it. With the PLL on BCLK
    instead, the audio sounds muffled.
  - The microSD card and the e-ink sit on the EYESPI breakout: board.SPI,
    SD CS on D24, e-ink CS D25, DC RX, RST TX, BUSY A3.
  - The NeoKey 1x4 (0x30) and the ANO (0x49) hang off STEMMA QT. The player
    runs without them.

The first start reads every file's tags into /FRISSON.IDX on the card (see
lib/library.py). Delete it after changing the music.

The player itself is lib/frisson.py. This file only reserves SRAM first:
CircuitPython compiles all of code.py before running it, and with the player
in here the compiler's memory left too little SRAM for the I2S DMA buffers
("Unable to allocate buffers for signed conversion", 10-27).

Libraries: adafruit_flac (the copy in lib/, which has seek()), adafruit_tlv320,
adafruit_seesaw, adafruit_bus_device. The screen driver, lib/fastscreen.py,
needs only built-in modules.
"""

import microcontroller

# 300 MHz gives FLAC decode headroom next to the e-ink and key polling.
microcontroller.cpu.frequency = 300_000_000

# Allocation order sets what lands in internal SRAM, and 24/96 only keeps up
# from SRAM (10-27: kernel and buffers in PSRAM decoded Zooropa at 0.9x real
# time, 1.3 underruns a second; in SRAM, 0 in 55 s).
#   1. adafruit_flac, so the turbo kernel's code is in SRAM
#   2. the output halves, and the I2S DMA buffers, reserved by playing them
#      once (the DMA copies come from SRAM, twice the whole buffer)
#   3. the decoder, before the library index and the screen take the rest
import adafruit_flac  # noqa: E402, F401
import audiobuf  # noqa: E402, F401
import frisson  # noqa: E402, F401
