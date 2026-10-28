# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Draws Menus.view() on the 2.13" 250x122 e-ink (Adafruit 6383, SSD1680Z,
ribbon FPC-7528B) with fast partial updates. Same interface as screen.py.

screen.py goes through displayio, which resets the panel, rewrites both RAMs
and runs the full 4-gray waveform on every refresh: 5.6 s, and refresh()
holds the loop for about 0.1 s. This drives the SSD1680 directly instead:

- the panel stays awake between updates
- updates use the controller's own partial waveform (OTP mode 2), which
  drives only the pixels that differ between RAM 0x26 (old) and 0x24 (new)
- each update is two 4000-byte SPI writes and a few commands; the loop never
  waits on BUSY
- a full refresh clears ghosting after FULL_EVERY partial updates, or once
  the screen has sat still for CLEAN_S seconds

Black and white only. The highlight bar is black with white text.

Text is Terminus 18 bold (fonts/ter-u18b.bdf, 10x18), read straight from the
BDF and stored already rotated into panel order, so drawing is only
bitmaptools blits.
"""

import time

import bitmaptools
import board
import digitalio
import displayio

W, H = 250, 122  # landscape, as drawn
PW, PH = 128, 250  # panel RAM: 122 sources (16 bytes a row) x 250 gates
CW, CH = 10, 18  # font cell
FONT = "/fonts/ter-u18b.bdf"
TITLE_Y = 12  # middle of the title
TOP = 25  # first row's top
LINE = 23  # row height
TAG_X = 46  # text after a tag starts here (4 characters of 10 px)
COLUMNS = 23  # characters across
IDLE = 0.05  # gathers a burst of wheel steps into one redraw
LIVE = 0.3  # during steady input, redraw at least this often (panel permitting)
FULL_EVERY = 40  # partial updates between full refreshes
CLEAN_S = 30  # a still screen with ghosting gets a full refresh after this

# outline and the rule under the title
RULES = ((0, 0, W, 2), (0, H - 2, W, 2), (0, 0, 2, H), (W - 2, 0, 2, H), (0, TOP - 3, W, 2))

BLACK, WHITE = 0, 1


def _out(pin, value):
    p = digitalio.DigitalInOut(pin)
    p.switch_to_output(value=value)
    return p


def load_font(path):
    """{char: (black ink, white ink)}, each a panel-order Bitmap(CH, CW)."""
    glyphs = {}
    code, rows = None, None
    with open(path) as f:
        for line in f:
            if line.startswith("ENCODING"):
                code = int(line.split()[1])
            elif line.startswith("BITMAP"):
                rows = [] if 32 <= code < 127 else None
            elif line.startswith("ENDCHAR"):
                if rows is not None:
                    black = displayio.Bitmap(CH, CW, 2)
                    white = displayio.Bitmap(CH, CW, 2)
                    black.fill(WHITE)
                    for gy, bits in enumerate(rows):
                        for gx in range(CW):
                            if bits & (0x8000 >> gx):
                                # landscape (gx, gy) -> panel (gy, CW - 1 - gx)
                                black[gy, CW - 1 - gx] = BLACK
                                white[gy, CW - 1 - gx] = WHITE
                    glyphs[chr(code)] = (black, white)
                rows = None
            elif rows is not None:
                hexdigits = line.strip()
                rows.append(int(hexdigits, 16) << (16 - 4 * len(hexdigits)))
    return glyphs


class Panel:
    """The SSD1680, driven over the SPI bus it shares with the SD card."""

    def __init__(self, spi):
        self.spi = spi
        self.cs = _out(board.D25, True)
        self.dc = _out(board.RX, True)
        self.rst = _out(board.TX, True)
        self.busy_pin = digitalio.DigitalInOut(board.A3)
        self.frame = displayio.Bitmap(PW, PH, 2)  # 1 = white
        self.buf = memoryview(self.frame)  # 16 bytes a row, leftmost pixel in bit 7
        self.old_due = False  # 0x26 still holds the frame before the last update
        self.rst.value = False
        time.sleep(0.01)
        self.rst.value = True
        time.sleep(0.01)
        self.cmd(0x12)  # soft reset
        self.wait()
        self.cmd(0x01, b"\xf9\x00\x00")  # 250 gates
        self.cmd(0x11, b"\x03")  # x and y increment
        self.cmd(0x44, b"\x00\x0f")  # x window, bytes 0 to 15
        self.cmd(0x45, b"\x00\x00\xf9\x00")  # y window, gates 0 to 249
        self.cmd(0x21, b"\x00\x80")  # as the 4-gray setup that put colstart 0 right
        self.cmd(0x18, b"\x80")  # internal temperature sensor

    @property
    def busy(self):
        return self.busy_pin.value

    def wait(self):
        while self.busy_pin.value:
            pass

    def cmd(self, c, data=b""):
        spi = self.spi
        while not spi.try_lock():
            pass
        try:
            spi.configure(baudrate=20_000_000)
            self.cs.value = False
            self.dc.value = False
            spi.write(bytes((c,)))
            self.dc.value = True
            if data:
                spi.write(data)
            self.cs.value = True
        finally:
            spi.unlock()

    def _ram(self, command):
        self.cmd(0x4E, b"\x00")
        self.cmd(0x4F, b"\x00\x00")
        self.cmd(command, self.buf)

    def keep_old(self):
        """Copy the frame on screen into 0x26, once the last update is done.
        Call before drawing the next frame."""
        if self.old_due and not self.busy:
            self._ram(0x26)
            self.old_due = False

    def full(self):
        """Full refresh of the frame (about 2 to 4 s, flashes). Blocks for
        the SPI writes only."""
        self.wait()
        self._ram(0x26)
        self._ram(0x24)
        self.cmd(0x3C, b"\x05")  # border white
        self.cmd(0x22, b"\xf7")
        self.cmd(0x20)
        self.old_due = False

    def partial(self):
        """Partial update to the frame. keep_old() must have run first."""
        self._ram(0x24)
        self.cmd(0x3C, b"\x80")  # border left alone
        self.cmd(0x22, b"\xfc")
        self.cmd(0x20)
        self.old_due = True


class EinkScreen:
    def __init__(self, spi, rows=4):
        displayio.release_displays()
        self.glyphs = load_font(FONT)
        self.panel = Panel(spi)
        self.nrows = rows
        self.drawn = -1  # Menus.version on screen
        self.input_at = 0.0
        self.changed_at = 0.0
        self.partials = 0
        self.draw({"title": "FRISSON", "right": "", "rows": [], "sel": -1})
        self.panel.full()

    def poke(self):
        """Note that a key was used just now."""
        self.input_at = time.monotonic()

    def update(self, menus, force=False):
        """Redraw if the view changed, input is idle and the panel is free.
        Returns True if an update started."""
        p = self.panel
        if p.busy:
            return False
        now = time.monotonic()
        if menus.version == self.drawn:
            if self.partials and now - self.changed_at >= CLEAN_S:
                p.full()
                self.partials = 0
                return True
            return False
        # Wait out a short burst of input, but not a long one: while the wheel
        # keeps turning, redraw each time the panel is free.
        if not force and now - self.input_at < IDLE and now - self.changed_at < LIVE:
            return False
        p.keep_old()
        self.draw(menus.view())
        self.drawn = menus.version
        self.changed_at = now
        if self.partials >= FULL_EVERY:
            p.full()
            self.partials = 0
        else:
            p.partial()
            self.partials += 1
        return True

    # drawing, in landscape coordinates

    def rect(self, x, y, w, h, value):
        bitmaptools.fill_region(self.panel.frame, y, PH - x - w, y + h, PH - x, value)

    def text(self, x, mid, s, ink=BLACK):
        """Like a displayio Label at (x, mid): mid is the middle of the cell."""
        frame = self.panel.frame
        px = mid - CH // 2
        py = PH - x - CW
        skip = WHITE if ink == BLACK else BLACK
        pick = 0 if ink == BLACK else 1
        g = self.glyphs
        for ch in s:
            if py < 0:
                break
            glyph = g.get(ch) or g["?"]
            bitmaptools.blit(frame, glyph[pick], px, py, skip_source_index=skip)
            py -= CW

    def draw(self, v):
        frame = self.panel.frame
        frame.fill(WHITE)
        for x, y, w, h in RULES:
            self.rect(x, y, w, h, BLACK)
        right = v["right"]
        self.text(6, TITLE_Y, v["title"][: COLUMNS - len(right) - 1])
        if right:
            self.text(W - 6 - CW * len(right), TITLE_Y, right)
        sel = v["sel"]
        if sel >= 0:
            self.rect(4, TOP + sel * LINE, W - 8, LINE - 1, BLACK)
        for i, (tag, text) in enumerate(v["rows"][: self.nrows]):
            mid = TOP + i * LINE + LINE // 2
            ink = WHITE if i == sel else BLACK
            if tag:
                self.text(6, mid, tag, ink)
            self.text(TAG_X if tag else 6, mid, text, ink)
