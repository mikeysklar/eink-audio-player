# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Frisson's menus: what the keys do, and what the screen shows.

  ANO wheel     move the highlight (volume on the now playing screen)
  ANO select    open the album, or play the track
  ANO up        back
  ANO down      now playing
  ANO left/right  page down / page up
  NeoKey 1 to 4 play, pause, reverse, forward
                (reverse restarts the track, or goes to the previous one
                in its first 3 seconds)
  hold NeoKey 3 / 4  rewind / fast-forward

No hardware here. Menus takes events from keys.Keys.poll(), calls a player
object (see frisson.py), and the screen reads view(). `version` goes up
whenever the view changes.
"""

ROWS = 4  # list rows on the screen
WIDTH = 19  # characters per row after a tag, 23 without (10 px each)


class Screen:
    def __init__(self, kind, title, items, cursor=0):
        self.kind = kind  # "albums", "tracks", "now"
        self.title = title
        self.items = items  # list of (tag, text, target)
        self.cursor = cursor
        self.top = 0


class Menus:
    def __init__(self, library, player):
        self.lib = library
        self.player = player
        self.version = 0
        self.stack = [self._albums()]

    # screens

    def _albums(self):
        items = [("", "%s - %s" % (a[0], a[1]) if a[0] else a[1], ("album", i))
                 for i, a in enumerate(self.lib.albums)]
        return Screen("albums", "ALBUMS  %d" % len(items), items)

    def _tracks(self, album, cursor=0):
        artist, title, indexes = self.lib.albums[album]
        items = []
        for n, i in enumerate(indexes):
            t = self.lib.tracks[i]
            items.append(("%02d" % (t[4] or n + 1), t[3], ("track", album, n)))
        return Screen("tracks", title.upper(), items, cursor)

    @property
    def top(self):
        return self.stack[-1]

    def _push(self, screen):
        self.stack.append(screen)
        self.version += 1

    def _back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.version += 1

    def _move(self, steps):
        s = self.top
        if not s.items:
            return
        cursor = max(0, min(len(s.items) - 1, s.cursor + steps))
        if cursor != s.cursor:
            s.cursor = cursor
            self.version += 1

    def _open(self, target):
        kind = target[0]
        if kind == "album":
            self._push(self._tracks(target[1]))
        elif kind == "track":
            _, album, n = target
            self.player.play(self.lib.albums[album][2], n)
            self.now_playing()

    def now_playing(self):
        if self.top.kind != "now":
            self._push(Screen("now", "NOW PLAYING", []))
        else:
            self.version += 1

    # input

    def handle(self, kind, value):
        """Act on one event from keys.Keys.poll()."""
        s = self.top
        p = self.player
        if kind == "key":
            if value == 0:
                if p.paused:
                    p.resume()
                elif not p.playing:
                    self._play_highlighted()
            elif value == 1:
                p.pause()
            elif value == 2:
                p.reverse()
            elif value == 3:
                p.forward()
            self.version += 1
        elif kind == "hold":
            p.scan(-1 if value == 2 else 1)
        elif kind == "wheel":
            if s.kind == "now":
                p.volume(value)
                self.version += 1
            else:
                self._move(value)
        elif kind == "button":
            if value == "select" and s.items:
                self._open(s.items[s.cursor][2])
            elif value == "up":
                self._back()
            elif value == "down" and p.current is not None:
                self.now_playing()
            elif value == "left":  # flipped to suit how the ANO is mounted
                self._move(ROWS)
            elif value == "right":
                self._move(-ROWS)

    def _play_highlighted(self):
        s = self.top
        if not s.items:
            return
        target = s.items[s.cursor][2]
        if target[0] == "album":
            self.player.play(self.lib.albums[target[1]][2], 0)
        elif target[0] == "track":
            self._open(target)

    # output

    def view(self):
        """What to draw: a dict with title, rows [(tag, text)], sel (the
        highlighted row or -1), right (text at the right of the title) and
        footer."""
        s = self.top
        p = self.player
        footer = ""
        if p.current is not None:
            t = self.lib.tracks[p.current]
            footer = "%s %s" % ("||" if p.paused else ">", t[3])
        if s.kind == "now":
            return self._view_now(footer)
        if s.cursor < s.top:
            s.top = s.cursor
        elif s.cursor >= s.top + ROWS:
            s.top = s.cursor - ROWS + 1
        rows = [(tag, text[:WIDTH if tag else WIDTH + 4]) for tag, text, _ in s.items[s.top : s.top + ROWS]]
        title = s.title
        right = "%d/%d" % (s.cursor + 1, len(s.items)) if s.items else ""
        return {"kind": s.kind, "title": title, "right": right, "rows": rows,
                "sel": s.cursor - s.top if s.items else -1, "footer": footer}

    def _view_now(self, footer):
        p = self.player
        if p.current is None:
            rows = [("", "nothing playing")]
        else:
            path, artist, album, title, number = self.lib.tracks[p.current]
            n, total = p.position()
            rows = [
                ("%02d" % (number or n), artist[:WIDTH]),
                ("", album[:WIDTH + 4]),
                ("", title[:WIDTH + 4]),
                ("", "%d/%d  %s  %d dB" % (n, total, "paused" if p.paused else "playing", p.db)),
            ]
        return {"kind": "now", "title": "NOW PLAYING", "right": "", "rows": rows,
                "sel": -1, "footer": "wheel volume   up back"}

    def text(self):
        """The view as plain text, for the serial console."""
        v = self.view()
        out = ["== %s  %s" % (v["title"], v["right"])]
        for i, (tag, text) in enumerate(v["rows"]):
            out.append("%s %3s %s" % (">" if i == v["sel"] else " ", tag, text))
        if v["footer"]:
            out.append("-- " + v["footer"])
        return "\n".join(out)
