# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Frisson's menus: what the keys do, and what the screen shows.

Two ways to find music:

Browse (the default)
  ANO wheel     move the highlight (volume on the now playing screen)
  ANO select    open the album, or play the track
  ANO up        back
  ANO down      now playing
  ANO left/right  page up / page down
  NeoKey 1 to 4 play, pause, reverse, forward
                (reverse restarts the track, or goes to the previous one
                in its first 3 seconds)
  hold NeoKey 3 / 4  rewind / fast-forward
  all 4 NeoKeys search

Search
  NeoKey chords type letters (Grippy alpha layer), with ANO left as the thumb
  ANO wheel     move through the results
  ANO select    open the artist or album, or play the track
  ANO up, or hold the thumb    leave search

No hardware here. Menus calls a player object (see code.py) and the screen
reads view(). `version` goes up whenever the view changes.
"""

ROWS = 4  # list rows on the screen
WIDTH = 19  # characters per row after a tag, 23 without (10 px each)

ALL_KEYS = (0, 1, 2, 3)


class Screen:
    def __init__(self, kind, title, items, cursor=0):
        self.kind = kind  # "albums", "artist", "tracks", "search", "now"
        self.title = title
        self.items = items  # list of (tag, text, target)
        self.cursor = cursor
        self.top = 0


class Menus:
    def __init__(self, library, player):
        self.lib = library
        self.player = player
        self.mode = "browse"  # or "search"
        self.query = ""
        self.version = 0
        self.stack = [self._albums()]

    # screens

    def _albums(self):
        items = [("", "%s - %s" % (a[0], a[1]) if a[0] else a[1], ("album", i))
                 for i, a in enumerate(self.lib.albums)]
        return Screen("albums", "ALBUMS  %d" % len(items), items)

    def _artist(self, name):
        items = [("", self.lib.albums[i][1], ("album", i)) for i in self.lib.albums_by(name)]
        return Screen("artist", name.upper(), items)

    def _tracks(self, album, cursor=0):
        artist, title, indexes = self.lib.albums[album]
        items = []
        for n, i in enumerate(indexes):
            t = self.lib.tracks[i]
            items.append(("%02d" % (t[4] or n + 1), t[3], ("track", album, n)))
        return Screen("tracks", title.upper(), items, cursor)

    def _search(self):
        items = []
        for kind, ref in self.lib.search(self.query):
            if kind == "artist":
                items.append(("ART", ref, ("artist", ref)))
            elif kind == "album":
                a = self.lib.albums[ref]
                items.append(("ALB", "%s - %s" % (a[1], a[0]), ("album", ref)))
            else:
                t = self.lib.tracks[ref]
                album = self._album_of(ref)
                n = self.lib.albums[album][2].index(ref)
                items.append(("SNG", "%s - %s" % (t[3], t[1]), ("track", album, n)))
        return Screen("search", "SEARCH", items)

    def _album_of(self, track):
        for i, a in enumerate(self.lib.albums):
            if track in a[2]:
                return i
        return 0

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
        if kind == "artist":
            self._push(self._artist(target[1]))
        elif kind == "album":
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

    def _enter_search(self):
        self.mode = "search"
        self.query = ""
        self._push(self._search())

    def _leave_search(self):
        self.mode = "browse"
        if self.top.kind == "search":
            self._back()
        self.version += 1

    # input

    def handle(self, kind, value):
        """Act on one event from ChordKeys.poll()."""
        if self.mode == "search":
            self._handle_search(kind, value)
        else:
            self._handle_browse(kind, value)

    def _handle_browse(self, kind, value):
        s = self.top
        p = self.player
        if kind == "menu":
            if value == ALL_KEYS:
                self._enter_search()
            elif value == (0,):
                if p.paused:
                    p.resume()
                elif not p.playing:
                    self._play_highlighted()
            elif value == (1,):
                p.pause()
            elif value == (2,):
                p.reverse()
            elif value == (3,):
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
            elif value == "left":
                self._move(-ROWS)
            elif value == "right":
                self._move(ROWS)

    def _play_highlighted(self):
        s = self.top
        if not s.items:
            return
        target = s.items[s.cursor][2]
        if target[0] == "album":
            self.player.play(self.lib.albums[target[1]][2], 0)
        elif target[0] == "track":
            self._open(target)

    def _handle_search(self, kind, value):
        if kind == "letter":
            if value == "\b":
                self.query = self.query[:-1]
            else:
                self.query += value
            self.stack[-1] = self._search()
            self.version += 1
        elif kind == "wheel":
            self._move(value)
        elif kind == "layer" and value == 1:  # thumb held: back to the menu layer
            self._leave_search()
        elif kind == "button":
            s = self.top
            if value == "select" and s.items:
                target = s.items[s.cursor][2]
                self.mode = "browse"
                self.stack.pop()  # back from the result goes where search started
                self._open(target)
                self.version += 1
            elif value == "up":
                self._leave_search()

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
        if s.kind == "search":
            title = "SEARCH " + self.query + "_"
            if not s.items:
                rows = [("", "type with chords" if len(self.query) < 1
                         else "no match for \"%s\"" % self.query)]
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
