# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Draws Menus.view() on the 2.13" 250x122 4-gray e-ink (Adafruit 6383,
SSD1680Z, ribbon FPC-7528B), set up as in the library's
ssd1680_2.13_grayscale_6383.py example, except colstart: the example's 8 cut
rows off this panel. 0 fit best of -8, 0, 2, 4, 8 and 16 (tested 10-27).

Four rows and the title in Terminus 18 bold (fonts/ter-u18b.bdf, 10x18).
Text is black. The highlight bar is light gray behind black text, and the
outline and rule are dark gray.

The quad-colour JD79661 panel this replaced took 40 s per refresh. update()
still redraws only once input has been idle for IDLE seconds and the panel
is free; anything that changes during a refresh is drawn by the next one.
"""

import time

import board
import displayio
import fourwire
import vectorio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

import adafruit_ssd1680

WHITE, LIGHT, DARK, BLACK = 0xFFFFFF, 0xAAAAAA, 0x555555, 0x000000
TEXT = BLACK  # titles, tags and rows
BAR = LIGHT  # highlight behind the selected row
RULE = DARK  # outline and the rule under the title
W, H = 250, 122
FONT = "/fonts/ter-u18b.bdf"
TITLE_Y = 12  # middle of the title
TOP = 25  # first row's top
LINE = 23  # row height
TAG_X = 46  # text after a tag starts here (4 characters of 10 px)
COLUMNS = 23  # characters across
IDLE = 0.5  # seconds of no input before a redraw

# outline and the rule under the title
RULES = ((0, 0, W, 2), (0, H - 2, W, 2), (0, 0, 2, H), (W - 2, 0, 2, H), (0, TOP - 3, W, 2))


def _fill(color):
    p = displayio.Palette(1)
    p[0] = color
    return p


class EinkScreen:
    def __init__(self, spi, rows=4):
        displayio.release_displays()
        bus = fourwire.FourWire(spi, command=board.RX, chip_select=board.D25, reset=board.TX,
                                baudrate=8_000_000)
        time.sleep(1)
        # seconds_per_frame: the driver's default makes us wait 180 s between
        # refreshes. The panel's busy pin already says when it is done.
        self.display = adafruit_ssd1680.SSD1680(
            bus, width=W, height=H, busy_pin=board.A3, rotation=270, colstart=0,
            vcom=0x1C, custom_lut=adafruit_ssd1680.FPC7519_LUT, grayscale=True,
            seconds_per_frame=1,
        )
        font = bitmap_font.load_font(FONT)
        font.load_glyphs("".join(chr(c) for c in range(32, 127)))
        rule = _fill(RULE)
        g = displayio.Group()
        g.append(vectorio.Rectangle(pixel_shader=_fill(WHITE), width=W, height=H))
        for x, y, w, h in RULES:
            g.append(vectorio.Rectangle(pixel_shader=rule, width=w, height=h, x=x, y=y))
        self.bar = displayio.Group(x=4, y=TOP)  # a Group, so it can be hidden
        self.bar.append(vectorio.Rectangle(pixel_shader=_fill(BAR), width=W - 8, height=LINE - 1))
        g.append(self.bar)
        self.title = label.Label(font, text="", color=TEXT, x=6, y=TITLE_Y)
        self.right = label.Label(font, text="", color=TEXT, anchor_point=(1.0, 0.5),
                                 anchored_position=(W - 6, TITLE_Y))
        g.append(self.title)
        g.append(self.right)
        self.tags, self.rows = [], []
        for i in range(rows):
            y = TOP + i * LINE + LINE // 2
            tag = label.Label(font, text="", color=TEXT, x=6, y=y)
            row = label.Label(font, text="", color=TEXT, x=6, y=y)
            self.tags.append(tag)
            self.rows.append(row)
            g.append(tag)
            g.append(row)
        self.display.root_group = g
        self.drawn = -1  # Menus.version on screen
        self.input_at = 0.0

    def poke(self):
        """Note that a key was used just now."""
        self.input_at = time.monotonic()

    def update(self, menus, force=False):
        """Redraw if the view changed, input is idle and the panel is free.
        Returns True if a refresh started (it blocks for about 0.3 s)."""
        if menus.version == self.drawn or self.display.busy:
            return False
        if not force and time.monotonic() - self.input_at < IDLE:
            return False
        self.draw(menus.view())
        self.drawn = menus.version
        self.display.refresh()
        return True

    def draw(self, v):
        right = v["right"]
        self.title.text = v["title"][: COLUMNS - len(right) - 1]
        self.right.text = right
        for i in range(len(self.rows)):
            tag, text = v["rows"][i] if i < len(v["rows"]) else ("", "")
            self.tags[i].text = tag
            self.rows[i].x = TAG_X if tag else 6
            self.rows[i].text = text
        self.bar.hidden = v["sel"] < 0
        if v["sel"] >= 0:
            self.bar.y = TOP + v["sel"] * LINE
