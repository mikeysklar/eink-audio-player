# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Draw Frisson's menus as PNGs, on the Mac, from a FRISSON.IDX.

Runs the real lib/menus.py through a few key presses and draws each view the
way lib/fastscreen.py lays it out, in Terminus 18 bold (fonts/ter-u18b.bdf).

    python3 draw_menus.py FRISSON.IDX out_dir

Needs Pillow.
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import library  # noqa: E402
import menus  # noqa: E402

W, H = 250, 122  # the rest as in lib/fastscreen.py
TITLE_Y, TOP, LINE, TAG_X, COLUMNS = 12, 25, 23, 46, 23
RULES = ((0, 0, W, 2), (0, H - 2, W, 2), (0, 0, 2, H), (W - 2, 0, 2, H), (0, TOP - 3, W, 2))
SCALE = 4
# how black and white look on the panel
INK = {"white": (236, 234, 226), "black": (24, 24, 24)}


def load_bdf(path):
    glyphs, cur, rows = {}, None, None
    for line in pathlib.Path(path).read_text(encoding="latin-1").splitlines():
        if line.startswith("FONTBOUNDINGBOX"):
            glyphs["box"] = [int(n) for n in line.split()[1:]]
        elif line.startswith("ENCODING"):
            cur = int(line.split()[1])
        elif line.startswith("BBX"):
            bbx = [int(n) for n in line.split()[1:]]
        elif line == "BITMAP":
            rows = []
        elif line == "ENDCHAR":
            glyphs[cur] = (bbx, rows)
            rows = None
        elif rows is not None:
            rows.append(int(line, 16))
    return glyphs


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), INK["white"])
        self.px = self.img.load()

    def rect(self, x, y, w, h, ink):
        for yy in range(max(0, y), min(H, y + h)):
            for xx in range(max(0, x), min(W, x + w)):
                self.px[xx, yy] = INK[ink]

    def text(self, font, x, y, s, ink, right=False):
        """Like a displayio Label at (x, y): y is the middle of the font's cell."""
        cw, ch_, _, descent = font["box"]
        if right:
            x -= cw * len(s)
        top = y - ch_ // 2
        for i, ch in enumerate(s):
            g = font.get(ord(ch)) or font.get(ord("?"))
            (bw, bh, bx, by), rows = g
            for r, bits in enumerate(rows):
                for c in range(bw):
                    if bits & (1 << (((bw + 7) // 8) * 8 - 1 - c)):
                        xx, yy = x + i * cw + bx + c, top + (ch_ + descent - by - bh) + r
                        if 0 <= xx < W and 0 <= yy < H:
                            self.px[xx, yy] = INK[ink]


def draw(view, big):
    c = Canvas()
    for x, y, w, h in RULES:
        c.rect(x, y, w, h, "black")
    if view["sel"] >= 0:  # black bar, white text
        c.rect(4, TOP + view["sel"] * LINE, W - 8, LINE - 1, "black")
    right = view["right"]
    c.text(big, 6, TITLE_Y, view["title"][: COLUMNS - len(right) - 1], "black")
    c.text(big, W - 6, TITLE_Y, right, "black", right=True)
    for i, (tag, text) in enumerate(view["rows"]):
        y = TOP + i * LINE + LINE // 2
        ink = "white" if i == view["sel"] else "black"
        if tag:
            c.text(big, 6, y, tag, ink)
        c.text(big, TAG_X if tag else 6, y, text, ink)
    return c.img.resize((W * SCALE, H * SCALE), Image.NEAREST)


class Index(library.Library):
    def __init__(self, path):
        tracks = []
        for line in pathlib.Path(path).read_text().splitlines():
            p = line.split("\t")
            tracks.append((p[0], p[1], p[2], p[3], int(p[4] or 0)))
        self._set(tracks)


class StandIn:
    """Enough of code.py's Player for the views."""

    def __init__(self):
        self.current, self.paused, self.queue, self.pos, self.db = None, False, [], 0, -16

    playing = property(lambda s: s.current is not None and not s.paused)

    def play(self, queue, pos):
        self.queue, self.pos, self.current = queue, pos, queue[pos]

    def position(self):
        return self.pos + 1, len(self.queue)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    reverse = forward = lambda s: None

    def volume(self, steps):
        self.db = max(-63, min(0, self.db + steps))


def main(index, out):
    big = load_bdf(pathlib.Path(__file__).resolve().parents[1] / "fonts" / "ter-u18b.bdf")
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lib = Index(index)
    m = menus.Menus(lib, StandIn())
    shots = []

    def shot(name):
        draw(m.view(), big).save(out / (name + ".png"))
        shots.append(name)

    shot("1-albums")
    pixies = next(i for i, a in enumerate(lib.albums) if "Doolittle" in a[1])
    m.handle("wheel", pixies)
    shot("2-albums-scrolled")
    m.handle("button", "select")
    m.handle("wheel", 2)
    shot("3-tracks")
    m.handle("button", "select")
    shot("4-now-playing")
    m.handle("key", 1)
    m.handle("wheel", -6)
    shot("5-now-paused")
    print("\n".join(shots))


if __name__ == "__main__":
    main(*sys.argv[1:3])
