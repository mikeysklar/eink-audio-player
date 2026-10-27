# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Grippy-style chord input from a NeoKey 1x4 and an ANO rotary encoder.

The four NeoKey keys are fingers 0 to 3 and one ANO button is the thumb (4),
the same five-button layout as Grippy (https://github.com/mikeysklar/grippy).
ChordKeys.thumb picks the button: "select" (the centre), "left", or None for
no thumb. A chord is sent when its first key is released.

Layers:
  1  MENU   chords come back as ("menu", combo), for code.py to act on
  2  ALPHA  chords come back as ("letter", "e"), from Grippy's alpha map

In MENU, holding NeoKey 3 or 4 alone for HOLD seconds sends ("hold", 2) or
("hold", 3), again every REPEAT seconds while held, and no chord on release.

Tap the thumb alone to switch to ALPHA. Hold it alone for LONG_HOLD
seconds to go back to MENU. Each switch comes back as ("layer", n).

The other ANO buttons and the wheel are not part of chords. They come back
as ("button", "select"|"up"|"down"|"left"|"right") on press and
("wheel", steps).

Libraries: adafruit_seesaw, adafruit_bus_device.
"""

import time

MENU = 1
ALPHA = 2

THUMB = 4

STABLE = 0.03  # a chord must hold this long to count (Grippy alpha timing)
DEBOUNCE_UP = 0.05  # ignore keys this long after a chord is sent
MENU_DEBOUNCE = 0.12
LONG_HOLD = 0.70  # thumb-only hold back to MENU
HOLD = 0.5  # NeoKey hold before rewind / fast-forward
REPEAT = 0.3  # then one ("hold", key) this often
HOLD_KEYS = ((2,), (3,))

# Grippy's alpha layer (src/chords_config.py), as characters. "\b" is backspace.
ALPHA_MAP = {
    (0,): "e",
    (1,): "i",
    (2,): "a",
    (3,): "s",
    (0, 1): "r",
    (0, 2): "o",
    (0, 3): "c",
    (1, 2): "n",
    (1, 3): "l",
    (2, 3): "t",
    (0, 1, 2): "d",
    (1, 2, 3): "p",
    (0, 1, 2, 3): "u",
    (0, 2, 3): " ",
    (0, 1, 3): "\b",
    (0, 4): "m",
    (1, 4): "g",
    (2, 4): "h",
    (3, 4): "b",
    (0, 1, 4): "y",
    (0, 2, 4): "w",
    (0, 3, 4): "x",
    (1, 2, 4): "f",
    (1, 3, 4): "k",
    (2, 3, 4): "v",
    (0, 1, 2, 4): "j",
    (1, 2, 3, 4): "z",
    (0, 1, 2, 3, 4): "q",
}


class ChordEngine:
    """The chord and layer logic, with no hardware.

    Call feed() with a bitmask of the five buttons (bit n = button n down)
    and the current time, often, even when nothing changes, so a long hold
    is seen. It returns a list of events, usually empty.
    """

    def __init__(self, layer=MENU):
        self.layer = layer
        self._last = ()
        self._pending = None
        self._sent = False
        self._changed_at = 0.0
        self._next_ok = 0.0
        self._thumb_at = 0.0
        self._gesture = False
        self._held = False
        self._hold_next = 0.0

    def feed(self, mask, now):
        combo = tuple(i for i in range(5) if mask & (1 << i))
        last = self._last
        self._last = combo
        events = []

        if now < self._next_ok:
            # Debounce: send nothing, but keep the edge state right, or the
            # next chord is dropped.
            if not combo and last:
                self._pending = None
                self._sent = False
            if combo != last:
                self._changed_at = now
                if not last:
                    self._pending = None
                    self._sent = False
            return events

        # Any finger down means a chord, not a thumb gesture. A lone thumb
        # left after the fingers lift is the tail of that chord.
        if any(i != THUMB for i in combo):
            self._gesture = False

        if combo == (THUMB,):
            if not last:
                self._thumb_at = now
                self._held = False
                self._gesture = True
            if self._gesture:
                if not self._held and now - self._thumb_at >= LONG_HOLD:
                    self._held = True
                    self._set_layer(MENU, events)
                return events

        if last == (THUMB,) and not combo and self._gesture:
            self._gesture = False
            if self._held:
                self._held = False
            else:
                self._set_layer(ALPHA, events)
            return events

        if combo != last:
            self._changed_at = now
            if not last:
                self._pending = None
                self._sent = False
        if combo and now - self._changed_at >= STABLE and combo != self._pending:
            self._pending = combo

        if self.layer == MENU and combo in HOLD_KEYS and now - self._changed_at >= HOLD:
            if now >= self._hold_next:
                events.append(("hold", combo[0]))
                self._hold_next = now + REPEAT
            self._sent = True  # no tap on release
            return events

        # Send on the first release.
        if len(combo) < len(last) and not self._sent:
            use = self._pending or last
            if use != (THUMB,):
                if self.layer == MENU:
                    events.append(("menu", use))
                else:
                    ch = ALPHA_MAP.get(use)
                    if ch is not None:
                        events.append(("letter", ch))
            self._sent = True
            self._next_ok = now + (MENU_DEBOUNCE if self.layer == MENU else DEBOUNCE_UP)

        if not combo and last:
            self._pending = None
            self._sent = False
        return events

    def _set_layer(self, layer, events):
        self._pending = None
        self._sent = False
        if layer != self.layer:
            self.layer = layer
            events.append(("layer", layer))


# seesaw pins
_NEOKEY_PINS = 0xF0  # keys 0 to 3 on pins 4 to 7
_ANO_BUTTONS = (
    (1 << 1, "select"), (1 << 2, "up"), (1 << 3, "left"), (1 << 4, "down"), (1 << 5, "right"),
)
_ANO_PINS = 0x3E
_ENCODER_BASE = 0x11
_ENCODER_DELTA = 0x40


class ChordKeys:
    """Reads the NeoKey and the ANO over I2C and feeds a ChordEngine.

    Call poll() from the main loop. It reads the boards at most every
    `interval` seconds and returns a list of events. Either board may be
    missing (`neokey` or `ano` is then None); with neither, ValueError.
    """

    def __init__(self, i2c, neokey_addr=0x30, ano_addr=0x49, interval=0.02, read_delay=0.001,
                 thumb="select"):
        from adafruit_seesaw.seesaw import Seesaw  # noqa: PLC0415

        self.engine = ChordEngine()
        self.thumb = thumb
        self.interval = interval
        # seesaw sleeps 8 ms per read by default, too long next to FLAC decode
        self.read_delay = read_delay
        self.neokey = self._open(Seesaw, i2c, neokey_addr, _NEOKEY_PINS)
        self.ano = self._open(Seesaw, i2c, ano_addr, _ANO_PINS)
        if self.neokey is None and self.ano is None:
            raise ValueError("no NeoKey at 0x%02x or ANO at 0x%02x" % (neokey_addr, ano_addr))
        self._ano_last = 0
        self._next = 0.0
        self._buf = bytearray(4)

    @staticmethod
    def _open(seesaw, i2c, addr, pins):
        try:
            board = seesaw(i2c, addr)
        except ValueError:  # not plugged in
            return None
        board.pin_mode_bulk(pins, seesaw.INPUT_PULLUP)
        return board

    @property
    def layer(self):
        return self.engine.layer

    def poll(self):
        now = time.monotonic()
        if now < self._next:
            return []
        self._next = now + self.interval

        # Buttons pull up, so a pressed button reads 0.
        keys = ano = 0
        if self.neokey:
            keys = ~self.neokey.digital_read_bulk(_NEOKEY_PINS, delay=self.read_delay) & _NEOKEY_PINS
        if self.ano:
            ano = ~self.ano.digital_read_bulk(_ANO_PINS, delay=self.read_delay) & _ANO_PINS
        mask = keys >> 4
        thumb = 0
        for bit, name in _ANO_BUTTONS:
            if name == self.thumb:
                thumb = bit
        if ano & thumb:
            mask |= 1 << THUMB
        events = self.engine.feed(mask, now)

        pressed = ano & ~self._ano_last & ~thumb
        self._ano_last = ano
        for bit, name in _ANO_BUTTONS:
            if pressed & bit:
                events.append(("button", name))

        if not self.ano:
            return events
        self.ano.read(_ENCODER_BASE, _ENCODER_DELTA, self._buf, delay=self.read_delay)
        steps = int.from_bytes(self._buf, "big")
        if steps & 0x80000000:
            steps -= 1 << 32
        if steps:
            events.append(("wheel", steps))
        return events
