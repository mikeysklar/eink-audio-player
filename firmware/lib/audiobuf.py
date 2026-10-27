# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""The I2S output and its buffer, allocated while SRAM is free (see code.py).

The I2S DMA copies come from internal SRAM, twice the whole buffer. Playing the
buffer once reserves them before anything else loads.
"""

from array import array

import audiobusio
import audiocore
import board

RATE = 96000  # sizes the buffer; lower rates get longer halves
BUFFER_MS = 64  # per half: 49 KB, plus 98 KB of DMA copies

out_buf = array("h", [0]) * (2 * (RATE * BUFFER_MS // 1000) * 2)
audio = audiobusio.I2SOut(board.A0, board.A1, board.A2)
audio.play(
    audiocore.RawSample(memoryview(out_buf), channel_count=2, sample_rate=RATE, single_buffer=False),
    loop=True,
)
audio.stop()
