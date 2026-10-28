# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""The music library on the microSD card: every .flac, with its tags.

Walking the card and reading every file's tags takes a while, so the result
is cached in INDEX on the card, one tab-separated line per track:

    path  artist  album  title  track number

Delete INDEX (or call Library.build) after changing the music on the card.

Tags come from the FLAC VORBIS_COMMENT block. A file without tags gets its
album from the folder name and its title from the file name.
"""

INDEX = "/FRISSON.IDX"


def _u32le(b, i):
    return b[i] | b[i + 1] << 8 | b[i + 2] << 16 | b[i + 3] << 24


def read_tags(f):
    """Return {"ARTIST": ..., "ALBUM": ..., "TITLE": ..., "TRACKNUMBER": ...}
    from an open FLAC file, or {} if it has no Vorbis comments."""
    head = f.read(4)
    if head[:3] == b"ID3":  # an ID3v2 tag in front of the FLAC stream
        rest = f.read(6)
        size = (rest[2] & 0x7F) << 21 | (rest[3] & 0x7F) << 14 | (rest[4] & 0x7F) << 7 | rest[5] & 0x7F
        f.seek(10 + size)
        head = f.read(4)
    if head != b"fLaC":
        return {}
    tags = {}
    while True:
        h = f.read(4)
        if len(h) < 4:
            return tags
        last = h[0] & 0x80
        size = h[1] << 16 | h[2] << 8 | h[3]
        if h[0] & 0x7F != 4:  # not VORBIS_COMMENT
            if last:
                return tags
            f.seek(size, 1)
            continue
        b = f.read(min(size, 8192))  # tags past 8 KB (lyrics, etc.) are skipped
        i = 4 + _u32le(b, 0)  # vendor string
        count = _u32le(b, i)
        i += 4
        for _ in range(count):
            if i + 4 > len(b):
                break
            n = _u32le(b, i)
            i += 4
            kv = b[i : i + n]
            i += n
            eq = kv.find(b"=")
            if eq > 0:
                key = kv[:eq].decode().upper()
                if key in ("ARTIST", "ALBUM", "TITLE", "TRACKNUMBER") and key not in tags:
                    tags[key] = str(kv[eq + 1 :], "utf-8").replace("\t", " ").strip()
        return tags


def _clean(text):
    return " ".join(text.replace("_", " ").split())


def _guess(path):
    """Artist, album and title from "/Artist-Album/01-title.flac"."""
    parts = path.split("/")
    folder = _clean(parts[-2]) if len(parts) > 2 else ""
    artist, album = "", folder
    for sep in (" - ", "-"):
        if sep in folder:
            artist, album = folder.split(sep, 1)
            break
    title = _clean(parts[-1][:-5])
    return artist.strip(), album.strip(), title


class Library:
    """Tracks and albums.

    tracks: list of (path, artist, album, title, number), sorted by artist,
            album, track number, path
    albums: list of (artist, album, [track indexes])
    """

    def __init__(self, vfs, progress=None):
        self.vfs = vfs
        try:
            self._load()
        except OSError:
            self.build(progress)

    def _load(self):
        tracks = []
        with self.vfs.open(INDEX, "r") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) == 5:
                    tracks.append((p[0], p[1], p[2], p[3], int(p[4] or 0)))
        self._set(tracks)

    def build(self, progress=None):
        """Walk the card, read every file's tags and rewrite INDEX."""
        paths = []
        self._walk("", paths)
        tracks = []
        for n, path in enumerate(paths):
            if progress:
                progress(n, len(paths))
            try:
                with self.vfs.open(path, "rb") as f:
                    tags = read_tags(f)
            except (OSError, ValueError, UnicodeError):
                tags = {}
            artist, album, title = _guess(path)
            number = tags.get("TRACKNUMBER", "").split("/")[0]
            tracks.append((
                path,
                tags.get("ARTIST") or artist,
                tags.get("ALBUM") or album,
                tags.get("TITLE") or title,
                int(number) if number.isdigit() else 0,
            ))
        with self.vfs.open(INDEX, "w") as f:
            for t in tracks:
                f.write("%s\t%s\t%s\t%s\t%d\n" % t)
        self._set(tracks)

    def _walk(self, folder, paths):
        for name, kind, *_ in self.vfs.ilistdir(folder or "/"):
            if name.startswith("."):  # also skips the macOS ._ files
                continue
            path = folder + "/" + name
            if kind == 0x4000:
                self._walk(path, paths)
            elif name.lower().endswith(".flac"):
                paths.append(path)

    def _set(self, tracks):
        tracks.sort(key=lambda t: (t[1].lower(), t[2].lower(), t[4], t[0]))
        self.tracks = tracks
        self.albums = []
        for i, t in enumerate(tracks):
            if self.albums and self.albums[-1][:2] == (t[1], t[2]):
                self.albums[-1][2].append(i)
            else:
                self.albums.append((t[1], t[2], [i]))
