# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
# Checker only, writes no files. Used while planning the routes, before running KiCad DRC.
"""Clearance, connectivity and preview for the hand-planned routes in plan.py.

Fast inner loop before KiCad's own DRC: every track segment and jumper pad
is checked against all other-net copper, the holes and the board edge, and
each net must come out as one connected piece.

  .../bin/python3 check_plan.py [out.png]
"""

import math
import os
import sys

import numpy as np

import netlist
import plan
import route
from plot_routes import write_png

GAP = 0.4
EDGE_GAP = 0.5
HOLE_GAP = 1.0      # M2.5 screw head
FINE_GAP = 0.2      # both inside plan.FINE_AREAS (the J4 fan)
JUMPER_GAP = 0.2    # a 0.4 track under an 0805, to that jumper's pads
S = 0.05            # preview mm per pixel


def seg_seg(a, b, c, d):
    """Min distance between segments ab and cd."""
    def pt_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2 = cross(a, b, c), cross(a, b, d)
    d3, d4 = cross(c, d, a), cross(c, d, b)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(pt_seg(a, c, d), pt_seg(b, c, d), pt_seg(c, a, b), pt_seg(d, a, b))


def seg_rect(a, b, r):
    x0, y0, x1, y1 = r
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1:
        return 0.0
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return min(seg_seg(a, b, p, q) for p, q in edges)


def rect_rect(r, s):
    dx = max(s[0] - r[2], r[0] - s[2], 0)
    dy = max(s[1] - r[3], r[1] - s[3], 0)
    return math.hypot(dx, dy)


class Shape:
    """seg: (a, b, w); rect: (x0, y0, x1, y1); circle: (x, y, r)."""

    def __init__(self, net, kind, g, label, fine=False):
        self.net, self.kind, self.g, self.label, self.fine = net, kind, g, label, fine

    def bbox(self):
        if self.kind == "seg":
            (a, b, w) = self.g
            return (min(a[0], b[0]) - w / 2, min(a[1], b[1]) - w / 2,
                    max(a[0], b[0]) + w / 2, max(a[1], b[1]) + w / 2)
        if self.kind == "circle":
            x, y, r = self.g
            return (x - r, y - r, x + r, y + r)
        return self.g

    def dist(self, o):
        """Edge-to-edge distance."""
        if self.kind == "seg" and o.kind == "seg":
            return seg_seg(self.g[0], self.g[1], o.g[0], o.g[1]) - self.g[2] / 2 - o.g[2] / 2
        if self.kind == "rect" and o.kind == "rect":
            return rect_rect(self.g, o.g)
        if self.kind == "rect":
            return o.dist(self)
        if o.kind == "rect":
            if self.kind == "seg":
                return seg_rect(self.g[0], self.g[1], o.g) - self.g[2] / 2
            x, y, r = self.g
            return seg_rect((x, y), (x, y), o.g) - r
        if o.kind == "circle":
            if self.kind == "circle":
                return math.hypot(self.g[0] - o.g[0], self.g[1] - o.g[1]) - self.g[2] - o.g[2]
            x, y, r = o.g
            return seg_seg(self.g[0], self.g[1], (x, y), (x, y)) - self.g[2] / 2 - r
        return o.dist(self)


def edge_dist(p, bx, by, bw, bh, r=3.0):
    px, py = p[0] - bx, p[1] - by
    cx = min(max(px, r), bw - r)
    cy = min(max(py, r), bh - r)
    if (px, py) != (cx, cy) and (px < r or px > bw - r) and (py < r or py > bh - r):
        return r - math.hypot(px - cx, py - cy)
    return min(px, bw - px, py, bh - py)


def build_shapes():
    pn = netlist.pad_net()
    board, (bx, by, bw, bh), pads, items, _, bodies = route.load_board(pn)
    shapes = []
    for (ref, num), rects in pads.items():
        if ref in plan.JUMPERS:
            continue  # the built board's jumpers; plan.py places its own
        for r in rects:
            shapes.append(Shape(pn.get((ref, num)), "rect", r, f"{ref}.{num}"))
    for it in items:
        if it.kind == "circle":
            x, y, r = it.geom
            shapes.append(Shape(None, "circle", (x, y, r - (route.HOLE_GAP - route.GAP)), it.label))
    tracks, jumpers = plan.routes(pads)

    def inside(b):
        return any(b[0] >= x0 and b[1] >= y0 and b[2] <= x1 and b[3] <= y1
                   for x0, y0, x1, y1 in plan.FINE_AREAS)
    for sh in shapes:
        sh.fine = inside(sh.bbox())
    for t in tracks:
        pts = plan.miter(t["pts"], t["chamfer"])
        for a, b in zip(pts, pts[1:]):
            sh = Shape(t["net"], "seg", (a, b, t["w"]), f"{t['net']} trk")
            sh.fine = inside(sh.bbox())
            shapes.append(sh)
    for j in jumpers:
        for p in (j["pa"], j["pb"]):
            pw, ph = plan.JP_PAD if j["horiz"] else plan.JP_PAD[::-1]
            shapes.append(Shape(j["net"], "rect", (p[0] - pw / 2, p[1] - ph / 2,
                                                   p[0] + pw / 2, p[1] + ph / 2),
                                f"{j['ref']}"))
    return (bx, by, bw, bh), shapes, tracks, jumpers, bodies


def check(geom, shapes, jumpers, bodies):
    bx, by, bw, bh = geom
    errs = []
    # the gap between each jumper's pads, where the hopped track runs
    body_of = {}
    for j in jumpers:
        cx, cy = j["center"]
        hx, hy = (0.4, 0.7) if j["horiz"] else (0.7, 0.4)
        body_of[j["ref"]] = (cx - hx, cy - hy, cx + hx, cy + hy)
    n = len(shapes)
    bbs = [s.bbox() for s in shapes]
    for i in range(n):
        si = shapes[i]
        if si.kind != "seg" and si.label.startswith(("J", "SW")) and not si.label.startswith("JP"):
            pass
        for j in range(i + 1, n):
            sj = shapes[j]
            if si.kind != "seg" and sj.kind != "seg" and not (
                    si.label.startswith("R") or sj.label.startswith("R")):
                continue  # pad-pad from footprints
            if si.net is not None and si.net == sj.net:
                continue
            need = HOLE_GAP if "circle" in (si.kind, sj.kind) else GAP
            if si.fine and sj.fine:
                need = FINE_GAP
            elif {si.kind, sj.kind} == {"seg", "rect"}:
                rr = si if si.kind == "rect" else sj
                sg = sj if rr is si else si
                if rr.label in body_of and sg.dist(Shape(None, "rect", body_of[rr.label],
                                                         "body")) <= 0:
                    need = JUMPER_GAP
            a, b = bbs[i], bbs[j]
            if a[0] - need > b[2] or b[0] - need > a[2] or a[1] - need > b[3] or b[1] - need > a[3]:
                continue
            d = si.dist(sj)
            if d < need - 1e-3:
                bi, bj = bbs[i], bbs[j]
                at = (round((max(bi[0], bj[0]) + min(bi[2], bj[2])) / 2, 2),
                      round((max(bi[1], bj[1]) + min(bi[3], bj[3])) / 2, 2))
                errs.append((round(d, 3), need, si.label, sj.label, at))
    for s in shapes:
        if s.kind == "seg":
            a, b, w = s.g
            for k in range(11):
                p = (a[0] + (b[0] - a[0]) * k / 10, a[1] + (b[1] - a[1]) * k / 10)
                if edge_dist(p, bx, by, bw, bh) - w / 2 < EDGE_GAP - 1e-3:
                    errs.append(("edge", s.label, p))
                    break
                for ref, (x0, y0, x1, y1) in bodies:
                    if ref == "SW1" and x0 - w / 2 < p[0] < x1 + w / 2 and y0 - w / 2 < p[1] < y1 + w / 2:
                        errs.append(("under SW1", s.label, p))
    # 0805 bodies (2.0 x 1.25) must not touch: two parts on one merged pad
    # cannot be placed or reworked. 0.2 mm leaves a visible gap.
    def body(j):
        cx, cy = j["center"]
        hx, hy = (1.0, 0.625) if j["horiz"] else (0.625, 1.0)
        return (cx - hx, cy - hy, cx + hx, cy + hy)
    for a in range(len(jumpers)):
        for b in range(a + 1, len(jumpers)):
            d = rect_rect(body(jumpers[a]), body(jumpers[b]))
            if d < 0.2 - 1e-6:
                errs.append(("jumper bodies", jumpers[a]["ref"], jumpers[b]["ref"], round(d, 3)))
    return errs


def split_nets(pads, tracks, jumpers):
    """KiCad sees a 0R as a part between two nets, so each jumper splits its
    net. The piece holding the net's first netlist pad keeps the name; each
    other piece is named after the jumpers it touches (EN_R4_R5). The
    pour's net (plan.POUR) is one net however its pieces lie: the fill
    joins them, and DRC checks that. A piece holding a plan.POCKETS pad
    takes that pocket's name.

    Returns ({(ref, pad): net} for footprint pads, {(jref, "a"|"b"): net},
    [net per track])."""
    pn = netlist.pad_net()
    shapes, keys = [], []
    for (ref, num), rects in pads.items():
        if (ref, num) in pn:
            for r in rects:
                shapes.append(Shape(pn[(ref, num)], "rect", r, ref))
                keys.append(("pad", (ref, num)))
    for k, t in enumerate(tracks):
        pts = plan.miter(t["pts"], t["chamfer"])
        for a, b in zip(pts, pts[1:]):
            shapes.append(Shape(t["net"], "seg", (a, b, t["w"]), "trk"))
            keys.append(("trk", k))
    for j in jumpers:
        pw, ph = plan.JP_PAD if j["horiz"] else plan.JP_PAD[::-1]
        for side, p in (("a", j["pa"]), ("b", j["pb"])):
            shapes.append(Shape(j["net"], "rect", (p[0] - pw / 2, p[1] - ph / 2,
                                                   p[0] + pw / 2, p[1] + ph / 2), j["ref"]))
            keys.append(("jp", (j["ref"], side)))
    parent = list(range(len(shapes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    bbs = [s.bbox() for s in shapes]
    for i in range(len(shapes)):
        for k in range(i + 1, len(shapes)):
            si, sk = shapes[i], shapes[k]
            if si.net != sk.net or (keys[i][0] == "jp" and keys[k][0] == "jp"
                                    and keys[i][1][0] == keys[k][1][0]):
                continue
            a, b = bbs[i], bbs[k]
            if a[0] > b[2] or b[0] > a[2] or a[1] > b[3] or b[1] > a[3]:
                continue
            if si.dist(sk) <= 1e-6:
                parent[find(i)] = find(k)
    name = {}
    for net, members in netlist.NETS.items():
        roots = {find(i) for i, s in enumerate(shapes) if s.net == net}
        first = next(i for i, kk in enumerate(keys) if kk == ("pad", members[0]))
        for root in roots:
            if net == plan.POUR:
                name[root] = next((k for k, pad in plan.POCKETS.items()
                                   if find(keys.index(("pad", pad))) == root), net)
            elif root == find(first):
                name[root] = net
            else:
                refs = sorted({keys[i][1][0] for i in range(len(shapes))
                               if keys[i][0] == "jp" and find(i) == root},
                              key=lambda r: int(r[1:]))
                name[root] = net + "_" + "_".join(refs)
    split = [n for n in name.values() if n != plan.POUR]  # its pieces meet in the fill
    if len(set(split)) != len(split):
        raise ValueError(f"sub-net names collide: {sorted(name.values())}")
    pad_out, jp_out, trk_out = {}, {}, [None] * len(tracks)
    for i, (kind, key) in enumerate(keys):
        n = name[find(i)]
        {"pad": pad_out, "jp": jp_out}.get(kind, {})[key] = n
        if kind == "trk":
            if trk_out[key] not in (None, n):
                raise ValueError(f"track {key} spans {trk_out[key]} and {n}")
            trk_out[key] = n
    for ref, side in jp_out:
        other = "b" if side == "a" else "a"
        if jp_out[(ref, side)] == jp_out[(ref, other)]:
            raise ValueError(f"{ref} shorted round by copper ({jp_out[(ref, side)]})")
    return pad_out, jp_out, trk_out


def connectivity(shapes, jumpers):
    """Each net one piece: same-net shapes touching, jumper pads linked."""
    by_net = {}
    for k, s in enumerate(shapes):
        if s.net and s.kind != "circle":
            by_net.setdefault(s.net, []).append(k)
    jp = {}
    for k, s in enumerate(shapes):
        if s.label.startswith("R") and s.kind == "rect":
            jp.setdefault(s.label, []).append(k)
    bad = {}
    for net, ks in by_net.items():
        if net == plan.POUR:
            continue  # joined by the fill, which DRC checks
        parent = {k: k for k in ks}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                if shapes[ks[a]].dist(shapes[ks[b]]) <= 1e-6:
                    parent[find(ks[a])] = find(ks[b])
        for lbl, pair in jp.items():
            if len(pair) == 2 and shapes[pair[0]].net == net:
                parent[find(pair[0])] = find(pair[1])
        groups = {}
        for k in ks:
            groups.setdefault(find(k), []).append(shapes[k].label)
        if len(groups) > 1:
            bad[net] = [sorted(set(g))[:6] for g in groups.values()]
    return bad


def render(path, geom, shapes, jumpers):
    bx, by, bw, bh = geom
    nx, ny = int(bw / S) + 1, int(bh / S) + 1
    X = bx + np.arange(nx) * S
    Y = by + np.arange(ny) * S
    PX, PY = np.meshgrid(X, Y)
    img = np.full((ny, nx, 3), 25, np.uint8)
    px, py = PX - bx, PY - by
    r = 3.0
    cx = np.clip(px, r, bw - r); cy = np.clip(py, r, bh - r)
    inside = np.hypot(px - cx, py - cy) <= r
    img[inside] = (20, 60, 35)
    # grid: every 1 mm faint, 5 mm brighter, 10 mm brightest
    for v, ax in ((X, 1), (Y, 0)):
        for k, c in enumerate(v):
            for step, col in ((10, (95, 95, 95)), (5, (60, 70, 60))):
                if abs(c / step - round(c / step)) < S / 2 / step:
                    if ax == 1:
                        img[:, k] = np.maximum(img[:, k], col)
                    else:
                        img[k, :] = np.maximum(img[k, :], col)
                    break
    nets = sorted({s.net for s in shapes if s.net})
    rng = np.random.RandomState(7)
    col = {nn: tuple(int(c) for c in rng.randint(90, 255, 3)) for nn in nets}
    col["GND"] = (60, 140, 255)
    col["3V3"] = (255, 80, 80)

    def paint(s, c):
        b = s.bbox()
        i0 = max(int((b[0] - bx) / S) - 1, 0); i1 = min(int((b[2] - bx) / S) + 2, nx)
        j0 = max(int((b[1] - by) / S) - 1, 0); j1 = min(int((b[3] - by) / S) + 2, ny)
        sx, sy = PX[j0:j1, i0:i1], PY[j0:j1, i0:i1]
        if s.kind == "rect":
            x0, y0, x1, y1 = s.g
            m = (sx >= x0) & (sx <= x1) & (sy >= y0) & (sy <= y1)
        elif s.kind == "circle":
            m = np.hypot(sx - s.g[0], sy - s.g[1]) <= s.g[2]
        else:
            m = route.seg_dist(sx, sy, *s.g[0], *s.g[1]) <= s.g[2] / 2
        img[j0:j1, i0:i1][m] = c
    for s in shapes:
        if s.kind == "circle":
            paint(s, (0, 0, 0))
        elif s.kind == "rect":
            if s.label.startswith("R"):
                paint(s, (255, 255, 255))
            else:
                paint(s, col.get(s.net, (110, 110, 110)) if s.net else (110, 110, 110))
    for s in shapes:
        if s.kind == "seg":
            paint(s, col[s.net])
    write_png(path, img)
    return col


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(route.HERE, "plan.png")
    geom, shapes, tracks, jumpers, bodies = build_shapes()
    errs = check(geom, shapes, jumpers, bodies)
    bad = connectivity(shapes, jumpers)
    for e in errs:
        print("CLEAR", e)
    for net, groups in bad.items():
        print("OPEN ", net, groups)
    _, jp, _ = split_nets(route.load_board(netlist.pad_net())[2], tracks, jumpers)
    for j in jumpers:
        print(f"  {j['ref']}: {jp[(j['ref'], 'a')]} | {jp[(j['ref'], 'b')]}")
    col = render(out, geom, shapes, jumpers)
    print(f"{len(errs)} clearance, {len(bad)} open nets, {len(jumpers)} jumpers -> {out}")


if __name__ == "__main__":
    main()
