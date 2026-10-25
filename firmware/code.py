# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""FLAC player for the eink-audio-player board.

Plays every .flac file in ALBUM on the microSD card, in name order, through
the TLV320DAC3100 to the headphone jack.

Board (see kicad/):
  - I2S on A0 BCLK, A1 WSEL, A2 DIN.
  - The TLV's MCLK comes from D5 over the TP1-TP2 jumper wire. D5 runs a
    15 MHz PWM clock and the TLV's PLL locks to it. With the PLL on BCLK
    instead, the audio sounds muffled.
  - The microSD card sits on the EYESPI breakout: board.SPI, CS on D24.

Libraries: adafruit_flac, adafruit_tlv320, adafruit_bus_device.
"""

from array import array

import audiobusio
import audiocore
import board

RATE = 44100  # sizes the buffer; 48 kHz files get slightly shorter halves
BUFFER_MS = 100  # per half. 64 ms underran: one FLAC frame can take 63 ms to decode

# The I2S DMA buffers come from a small internal-RAM heap. Reserve them before
# anything else loads, by playing the output buffer once. Importing the FLAC
# decoder and the SD driver first leaves too little room, and
# FLACPlayer.play then fails with "Unable to allocate buffers".
out_buf = array("h", [0]) * (2 * (RATE * BUFFER_MS // 1000) * 2)
audio = audiobusio.I2SOut(board.A0, board.A1, board.A2)
audio.play(
    audiocore.RawSample(memoryview(out_buf), channel_count=2, sample_rate=RATE, single_buffer=False),
    loop=True,
)
audio.stop()

import time  # noqa: E402

import pwmio  # noqa: E402
import sdcardio  # noqa: E402
import storage  # noqa: E402

import adafruit_flac  # noqa: E402
import adafruit_tlv320  # noqa: E402

ALBUM = "/Shpongle-Tales_Of_The_Inexpressible-2001"
LEVEL = 0.5  # FLACPlayer output level, 0.0 to 1.0
DAC_DB = -16  # TLV320 DAC volume
MCLK_HZ = 15_000_000

mclk = pwmio.PWMOut(board.D5, frequency=MCLK_HZ, duty_cycle=32768)

# Read the card through the VfsFat object, so CIRCUITPY needs no /sd folder.
sd = sdcardio.SDCard(board.SPI(), board.D24, baudrate=24_000_000)
vfs = storage.VfsFat(sd)
tracks = sorted(
    name
    for name, *_ in vfs.ilistdir(ALBUM)
    if name.lower().endswith(".flac") and not name.startswith(".")  # skip macOS ._ files
)
print(len(tracks), "tracks in", ALBUM)

dac = adafruit_tlv320.TLV320DAC3100(board.I2C())
player = adafruit_flac.FLACPlayer(audio, buffer=out_buf, level=LEVEL)
decoder = None
rate = 0

for name in tracks:
    with vfs.open(ALBUM + "/" + name, "rb") as f:
        if decoder is None:
            decoder = adafruit_flac.FLACDecoder(f)
        else:
            decoder.open(f)
        if decoder.sample_rate != rate:
            rate = decoder.sample_rate
            dac.configure_clocks(sample_rate=rate, bit_depth=16, mclk_freq=MCLK_HZ)
            dac.headphone_output = True
            dac.dac_volume = DAC_DB
        print(
            "%s  %d Hz %d-bit %d:%02d"
            % (name, rate, decoder.source_bits_per_sample, decoder.duration // 60, decoder.duration % 60)
        )

        player.play(decoder)
        start = last = time.monotonic_ns()
        busy = slowest = decoded = 0
        while player.playing:
            t = time.monotonic_ns()
            before = decoder.samples_decoded
            player.update()
            took = time.monotonic_ns() - t
            if decoder.samples_decoded != before:
                busy += took
                slowest = max(slowest, took)
                decoded += decoder.samples_decoded - before
            if t - last >= 30_000_000_000:
                # load: time spent decoding per second of audio decoded
                print(
                    "  %3ds load %d%% slowest %d ms underruns %d"
                    % ((t - start) // 10**9, busy * rate // 10**7 // max(1, decoded),
                       slowest // 10**6, player.underruns)
                )
                last = t
                busy = slowest = decoded = 0
        print("  done, underruns", player.underruns)
