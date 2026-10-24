// Anatomy figure of the E-ink Audio Player: a milled single-sided board that carries a
// Feather RP2350, a TLV320DAC3100 DAC and an EYESPI breakout on sockets, with a
// LiPo, a 2.13in e-ink and a NeoKey 1x4 on its back.
//
//   node build.mjs --light          -> eink-audio-player-light.html
//   node build.mjs --light --hero   -> eink-audio-player-hero-light.html (no hint, for record.mjs)
//
// Every number is in mm and comes from the design: pcb.json (dump_pcb.py over
// eink-audio-player.kicad_pcb: tracks, pads, zone fills, footprints) and solids.json
// (solids.py over case/build/board.step: every solid's global bounding box). Frame:
// STEP frame, x east, y north (board bottom-left at 0,0), z up, board top at 1.51.
//
// Pose: as on the stand (enclosure/layout.json), seen from behind and to the left, the
// way the Blender renders show the back. Everything is drawn in the board's frame, from
// the camera direction that pose gives, and the whole figure is then turned flat in 2D so
// the desk is level. The NeoKey and the ANO keep their stand pose relative to the board.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { KIT } from "./kit-dir.mjs";
import { polyPaths, pbPrism, pbFrustum, pbRoundRect } from "./poly.mjs";
const k = await import(`${KIT}/kit/iso-kit.mjs`);
const G = await import(`${KIT}/kit/lathe.mjs`);
const { kitScript } = await import(`${KIT}/scripts/inline-kit.mjs`);

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "out");
const theme = process.argv.includes("--light") ? "light" : "dark";
const hero = process.argv.includes("--hero");
const pcb = JSON.parse(readFileSync(join(HERE, "pcb.json"), "utf8"));
const solids = JSON.parse(readFileSync(join(HERE, "solids.json"), "utf8"));

const S = 4; // world units per mm
const WIDTH = 600;

// ---- design numbers ----
const BOARD = { x0: 0.05, x1: 61.01, y0: 0.05, y1: 76.11, t: 1.51, r: 3.0 };
const CU = 1.55;
const SOCK_TOP = 8.995;          // PinSocket_*_SMD bbox top
const PLASTIC_TOP = 11.495;      // plug-in board underside (header plastic 2.5 mm)
const PIN_LOW = 2.955;           // EYESPI jp1/jp2 pins reach down to here
const PIN = 0.64;
const FEATHER = { x0: 10.21, x1: 61.01, y0: 29.45, y1: 52.31, z0: 11.495, z1: 13.065, r: 2.5 };
const TLV = { x0: 29.26, x1: 61.01, y0: 1.51, y1: 26.91, z0: 11.495, z1: 13.065, r: 2.5 };
const EYE = { x0: 17.83, x1: 43.23, y0: 56.87, y1: 74.65, z0: 11.495, z1: 13.095, r: 1.5 };
const BATT = { x0: 12.03, x1: 49.03, y0: 8.08, y1: 68.08, z0: -7.585, z1: -0.085 };
// MX switch and keycap (3d/make_mx_wrl.py, Cherry datasheet sizes), on the NeoKey's
// outer face at z -12.115, key centres from measure_neokey_sw1.json.
const NK_FACE = -12.115;
const KEYS = [1.955, 21.005, 40.055, 59.105].map((x) => [x, 18.395]);
// ANO rotary encoder (6310): not on this board but on the stand, past the keys' right end
// and toward the player, in their plane (build_pcb.py ANO1). Board frame from the STEP: PCB
// front (wheel side) at z -21.745, back -20.235; wheel up to -27.545.
const ANO = { x0: -53.61, x1: -12.97, y0: -36.27, y1: -0.71, cx: -33.285, cy: -18.466, zf: -21.745, zb: -20.235 };

// ---- explode ----
const LIFT = 28;                 // top-side boards come straight up off their sockets
const DROP = 20;                 // the LiPo drops straight down
const D_HINGE = [78.5, -4.0];     // the e-ink swings open about the flex at the top edge
// The stand: board ("stack") and NeoKey ("keys") body frames, world mm, desk Z=0, player at -Y.
const LAYOUT = JSON.parse(readFileSync(join(HERE, "..", "enclosure", "layout.json"), "utf8"));
const SB = LAYOUT.stack, KB = LAYOUT.keys;
const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const toBoard = (w) => [dot3(SB.bx, w), dot3(SB.by, w), dot3(SB.bz, w)];   // a world direction
// The NeoKey (and the ANO, in its frame) relative to the board: a turn about x and a shift.
const K_A = Math.atan2(dot3(SB.bz, KB.by), dot3(SB.by, KB.by));
const K_T = toBoard(KB.p0.map((v, i) => v - SB.p0[i]));
// Taken apart, the keys and the ANO slide out together to the player's left, and up.
const K_OUT = toBoard([-95, 0, 15]);
const kPose = (p, m) => { const q = rotYZ(p, [0, 0], K_A); return q.map((v, i) => v + K_T[i] + K_OUT[i] * m); };

const footprint = (ref) => pcb.footprints.find((f) => f.ref === ref);
const padsOf = (ref) => pcb.pads.filter((p) => p.ref === ref && p.num);
const netBase = (n) => n.replace(/^\//, "").replace(/_R[1-4]$/, "");

// ---- solids from the STEP ----
// Groups match on the Adafruit product ID (FreeCAD suffixes repeated labels). Each model is
// Adafruit's parts on a KiCad board export: its layers (<board>_PCB, _pad, _silkscreen,
// _soldermask, _copper) are drawn here by hand, so they are skipped.
const BOARD_LAYER = /_(PCB|pad|silkscreen|soldermask|copper)\d*$/;
function compsOf(group, skip = () => false) {
  const map = new Map();
  const pid = group.split(" ")[0];
  for (const s of solids) {
    if (!s.path[1] || s.path[1].split(" ")[0] !== pid) continue;
    const parent = s.path[s.path.length - 1];
    const key = parent.startsWith("PCB Component") || s.path.length === 3 ? s.label : parent;
    if (BOARD_LAYER.test(key) || BOARD_LAYER.test(s.label) || skip(key, s)) continue;
    const b = s.bb;
    const m = map.get(key);
    map.set(key, m ? [Math.min(m[0], b[0]), Math.max(m[1], b[1]), Math.min(m[2], b[2]), Math.max(m[3], b[3]), Math.min(m[4], b[4]), Math.max(m[5], b[5])] : [...b]);
  }
  return [...map.entries()].map(([key, bb]) => ({ key, bb }));
}

// ---- camera ----
// The kit's floor has y pointing south (its plans are drawn like SVG), so north is -y.
const W3 = ([x, y, z]) => [x * S, -y * S, z * S];
function rotYZ([x, y, z], [hy, hz], a) {
  const c = Math.cos(a), s = Math.sin(a), dy = y - hy, dz = z - hz;
  return [x, hy + dy * c - dz * s, hz + dy * s + dz * c];
}
const smooth = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const corners = (b) => [0, 1].flatMap((i) => [2, 3].flatMap((j) => [4, 5].map((m) => [b[i], b[j], b[m]])));
const DISPLAY_BB = [0.04, 62.15, 36.74, 76.11, -12.631, -7.627];
const NEOKEY_BB = [-7.57, 68.63, 7.6, 29.19, -33.615, -8.71];
const ANO_BB = [ANO.x0, ANO.x1, ANO.y0, ANO.y1, -27.545, -17.2];
const fitPts = [
  ...corners([0, 61.96, 0, 76.11, 0, 9]),
  ...corners([10.21, 62.21, 29.45, 52.31, 2.9, 17.87 + LIFT]),
  ...corners([29.26, 62.8, 1.51, 26.91, 2.9, 18.07 + LIFT]),
  ...corners([17.83, 43.23, 56.87, 77.5, 2.9, 15.2 + LIFT]),
  ...corners([BATT.x0, BATT.x1, BATT.y0, BATT.y1, BATT.z0 - DROP, 0]),
];
for (let a = 0; a <= 180; a += 10) {
  fitPts.push(...corners(DISPLAY_BB).map((p) => rotYZ(p, D_HINGE, (a * Math.PI) / 180)));
  fitPts.push(...[NEOKEY_BB, ANO_BB].flatMap(corners).map((p) => kPose(p, a / 180)));
}
// Camera: from behind the stand and to the player's left (world toward-viewer vector V_W).
// In the board's frame that is the kit camera CAM; TURN is the 2D map from that view to
// the world view (same direction, so a pure turn), which levels the desk.
const deg = Math.PI / 180;
const V_W = [-Math.sin(35 * deg) * Math.cos(25 * deg), Math.cos(35 * deg) * Math.cos(25 * deg), Math.sin(25 * deg)];
const vb = toBoard(V_W);
const CAM = { azimuth: Math.atan2(-vb[1], vb[0]) / deg, elevation: Math.asin(vb[2]) / deg };
const CAM_W = { azimuth: Math.atan2(-V_W[1], V_W[0]) / deg, elevation: Math.asin(V_W[2]) / deg };
const TURN = (() => {
  const pb = { origin: [0, 0], scale: 1, ...CAM }, pw = { origin: [0, 0], scale: 1, ...CAM_W };
  const world = (p) => [0, 1, 2].map((i) => SB.p0[i] + p[0] * SB.bx[i] + p[1] * SB.by[i] + p[2] * SB.bz[i]);
  const b = (p) => k.iso(W3(p), pb), w = (p) => k.iso(W3(world(p)), pw);
  const sub = (a, c) => [a[0] - c[0], a[1] - c[1]];
  const o = [0, 0, 0], ex = [10, 0, 0], ey = [0, 10, 0];
  const b1 = sub(b(ex), b(o)), b2 = sub(b(ey), b(o)), w1 = sub(w(ex), w(o)), w2 = sub(w(ey), w(o));
  const det = b1[0] * b2[1] - b2[0] * b1[1];
  const inv = [[b2[1] / det, -b2[0] / det], [-b1[1] / det, b1[0] / det]];
  const A = [[w1[0] * inv[0][0] + w2[0] * inv[1][0], w1[0] * inv[0][1] + w2[0] * inv[1][1]],
             [w1[1] * inv[0][0] + w2[1] * inv[1][0], w1[1] * inv[0][1] + w2[1] * inv[1][1]]];
  const ez = [0, 0, 10], bz = sub(b(ez), b(o)), wz = sub(w(ez), w(o));
  const err = Math.hypot(A[0][0] * bz[0] + A[0][1] * bz[1] - wz[0], A[1][0] * bz[0] + A[1][1] * bz[1] - wz[1]);
  console.log("camera", CAM.azimuth.toFixed(1), CAM.elevation.toFixed(1), "turn det", (A[0][0] * A[1][1] - A[0][1] * A[1][0]).toFixed(4), "check", err.toFixed(6));
  return A;
})();
const turned = (p) => { const q = k.iso(W3(p), { origin: [0, 0], scale: 1, ...CAM }); return [TURN[0][0] * q[0] + TURN[0][1] * q[1], TURN[1][0] * q[0] + TURN[1][1] * q[1]]; };
const FIT = (() => {
  const flat = fitPts.map(turned);
  const xs = flat.map((p) => p[0]), ys = flat.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const height = Math.round(((WIDTH - 28) * (y1 - y0)) / (x1 - x0) + 28);
  const scale = (WIDTH - 28) / (x1 - x0);
  return { height, scale, shift: [WIDTH / 2 - ((x0 + x1) / 2) * scale, height / 2 - ((y0 + y1) / 2) * scale] };
})();
const HEIGHT = FIT.height;
const P = { origin: [0, 0], scale: FIT.scale, ...CAM };
const POSE = `matrix(${[TURN[0][0], TURN[1][0], TURN[0][1], TURN[1][1], ...FIT.shift].map((v) => v.toFixed(5)).join(" ")})`;
console.log("viewBox", WIDTH, HEIGHT, "scale", P.scale.toFixed(3));

// ---- helpers ----
const at = (p) => k.iso(W3(p), P);
const fmt = ([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`;
const poly = (points, closed = true) => `M${points.map((p) => fmt(at(p))).join("L")}${closed ? "Z" : ""}`;
const S_ = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const box = (x0, x1, y0, y1, z0, z1, { r = 0, steps = 3, bevel = 0 } = {}) =>
  k.slabOf({ x: x0 * S, y: -y1 * S, w: (x1 - x0) * S, d: (y1 - y0) * S, r: r * S }, z0 * S, (z1 - z0) * S, P, steps, bevel);
const onTop = (points, z, closed = true) => k.onTop(points.map(([x, y]) => [x * S, -y * S]), z * S, P, closed);
const rect = (x0, x1, y0, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
const circle = (cx, cy, r, n = 24) => Array.from({ length: n }, (_, i) => [cx + r * Math.cos((i / n) * 2 * Math.PI), cy + r * Math.sin((i / n) * 2 * Math.PI)]);
const depth = (p) => k.depthOf(W3(p), P);
const centre = (b) => [(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2];
const farFirst = (list, key) => [...list].sort((a, b) => depth(key(a)) - depth(key(b)));
const wrap = (g, inner) => `<g data-g="${g}">${inner}</g>`;
const plan = (b) => ({ x: b.x0 * S, y: -b.y1 * S, w: (b.x1 - b.x0) * S, d: (b.y1 - b.y0) * S, r: b.r * S });

// ---- board: substrate, copper, holes ----
function padBoard() {
  return S_(k.slabOf(plan(BOARD), 0, BOARD.t * S, P, 8), { tone: "hi" });
}

function stadium(a, b, w) {
  const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1;
  const ang = Math.atan2(dy, dx), h = w / 2, out = [];
  for (let i = 0; i <= 6; i++) { const t = ang + Math.PI / 2 + (i / 6) * Math.PI; out.push([a[0] + h * Math.cos(t), a[1] + h * Math.sin(t)]); }
  for (let i = 0; i <= 6; i++) { const t = ang - Math.PI / 2 + (i / 6) * Math.PI; out.push([b[0] + h * Math.cos(t), b[1] + h * Math.sin(t)]); }
  return out;
}

function copper() {
  const nets = new Map();
  const add = (net, d) => { if (!nets.has(net)) nets.set(net, []); nets.get(net).push(d); };
  for (const z of pcb.zones) {
    if (!z.filled.length) continue;
    for (const f of z.filled) add(netBase(z.net), onTop(f.outline, CU) + f.holes.map((h) => onTop(h, CU)).join(""));
  }
  for (const t of pcb.tracks) add(netBase(t.net), onTop(stadium(t.a, t.b, t.w), CU));
  for (const p of pcb.pads) {
    if (!p.smd) continue;
    const [x0, y0, x1, y1] = p.bbox;
    add(p.net && !p.net.startsWith("unconnected") ? netBase(p.net) : "", onTop(rect(x0, x1, y0, y1), CU));
  }
  const groove = `<path class="lp-groove" d="${onTop(k.ringOf(plan(BOARD), 8).map(([x, y]) => [x / S, -y / S]), CU)}"/>`;
  const edges = [], fills = [];
  for (const [net, list] of nets) {
    const attr = net ? ` data-net="${net}"` : "";
    edges.push(`<g${attr}><path class="iso-line lp-cu-edge" data-tone="lo" fill-rule="evenodd" d="${list.join("")}"/></g>`);
    fills.push(`<g${attr}><path class="lp-cu-fill" fill-rule="evenodd" d="${list.join("")}"/></g>`);
  }
  // Mounting holes, M2.5, through the board; the fill keeps its clearance round them.
  const holes = pcb.footprints.filter((f) => f.ref.startsWith("H")).map((f) => {
    const ring = circle(f.pos[0], f.pos[1], 1.35, 28);
    return `<path class="lp-hole" d="${onTop(ring, CU)}"/>` + L(onTop(ring, CU), { tone: "mid" });
  });
  return groove + edges.join("") + fills.join("") + holes.join("");
}

// ---- parts soldered to the board ----
function socket(ref, g) {
  const pads = padsOf(ref);
  const fp = footprint(ref);
  const cy = fp.pos[1];
  const xs = pads.map((p) => p.pos[0]);
  const x0 = Math.min(...xs) - 1.27, x1 = Math.max(...xs) + 1.27;
  const y0 = cy - 1.27, y1 = cy + 1.27;
  const legs = (side) => pads.filter((p) => (p.pos[1] > cy) === (side > 0)).map((p) => {
    const [, py0, , py1] = p.bbox;
    const ly0 = side > 0 ? y1 : py0 + 0.15, ly1 = side > 0 ? py1 - 0.15 : y0;
    const lit = p.net && !p.net.startsWith("unconnected") ? ` data-net="${netBase(p.net)}"` : "";
    return `<g${lit}>${S_(box(p.pos[0] - PIN / 2, p.pos[0] + PIN / 2, ly0, ly1, CU, CU + 0.3), { tone: "mid", crease: "none" })}</g>`;
  });
  const seams = xs.slice(1).map((x) => x - 1.27);
  const inner = [
    ...seams.map((x) => L(onTop([[x, y0], [x, y1]], SOCK_TOP, false), { tone: "faint" })),
    ...seams.map((x) => L(k.rise([x * S, -y0 * S], CU * S, SOCK_TOP * S, P), { tone: "faint" })),
  ].join("");
  const body = S_(box(x0, x1, y0, y1, CU, SOCK_TOP, { r: 0.15, bevel: 0.25 }), { tone: "mid", inner });
  const mouths = xs.map((x) => {
    const sq = rect(x - 0.5, x + 0.5, cy - 0.5, cy + 0.5);
    return `<path class="lp-hole" d="${onTop(sq, SOCK_TOP)}"/>` + L(onTop(sq, SOCK_TOP), { tone: "lo" });
  }).join("");
  return { key: [(x0 + x1) / 2, cy, 4], svg: wrap(g, legs(+1).join("") + body + mouths + legs(-1).join("")) };
}

function jumper(ref) {
  const f = footprint(ref);
  const [cx, cy] = f.pos;
  const x0 = cx - 0.6, x1 = cx + 0.6, y0 = cy - 1.0, y1 = cy + 1.0, z0 = CU, z1 = 2.045;
  const caps = [[y0, y0 + 0.45], [y1 - 0.45, y1]];
  const svg = S_(box(x0, x1, caps[1][0], caps[1][1], z0, z1, { r: 0.05 }), { tone: "mid", crease: "faint" }) +
    S_(box(x0 + 0.03, x1 - 0.03, y0 + 0.45, y1 - 0.45, z0, z1 - 0.03), { tone: "mid" }) +
    S_(box(x0, x1, caps[0][0], caps[0][1], z0, z1, { r: 0.05 }), { tone: "mid", crease: "faint" });
  return { key: [cx, cy, 1.8], svg: wrap(`jumper ${ref.toLowerCase()}`, svg) };
}

function slideSwitch() {
  const out = [];
  for (const p of padsOf("SW1")) {
    const [x0, y0, x1, y1] = p.bbox;
    out.push(S_(box(x0 + 0.1, 55.96, (y0 + y1) / 2 - 0.3, (y0 + y1) / 2 + 0.3, CU, CU + 0.3), { tone: "mid", crease: "none" }));
  }
  const inner = L(onTop([[56.4, 29.7], [60.2, 29.7], [60.2, 35.96], [56.4, 35.96]], 3.095), { tone: "faint" });
  out.push(S_(box(55.96, 60.66, 29.23, 36.43, CU, 3.095, { r: 0.1, bevel: 0.2 }), { tone: "mid", inner }));
  out.push(S_(box(60.66, 61.96, 32.82, 34.32, 1.795, 2.895, { r: 0.1 }), { tone: "mid" }));
  return { key: [58.3, 32.8, 2.3], svg: wrap("sw1", out.join("")) };
}

// ---- plug-in boards ----
const HEADERS = { feather: ["J1", "J2"], tlv: ["J9", "J10"], eye: ["J4", "J5"] };
function headerRow(ref) {
  const xs = padsOf(ref).map((p) => p.pos[0]).sort((a, b) => a - b);
  return { xs, cy: footprint(ref).pos[1] };
}
function headerPlastic(ref) {
  const { xs, cy } = headerRow(ref);
  const x0 = xs[0] - 1.27, x1 = xs[xs.length - 1] + 1.27, y0 = cy - 1.27;
  const inner = xs.slice(1).map((x) => L(k.rise([(x - 1.27) * S, -y0 * S], SOCK_TOP * S, PLASTIC_TOP * S, P), { tone: "faint" })).join("");
  return S_(box(x0, x1, y0, cy + 1.27, SOCK_TOP, PLASTIC_TOP, { r: 0.1 }), { tone: "mid", inner });
}
function headerPins(ref) {
  const { xs, cy } = headerRow(ref);
  return farFirst(xs, (x) => [x, cy, 0]).map((x) => S_(box(x - PIN / 2, x + PIN / 2, cy - PIN / 2, cy + PIN / 2, PIN_LOW, SOCK_TOP), { tone: "mid", crease: "none" })).join("");
}
function pinTails(ref, top) {
  const { xs, cy } = headerRow(ref);
  return farFirst(xs, (x) => [x, cy, 0]).map((x) => {
    const pad = circle(x, cy, 0.85, 16);
    return `<path class="lp-solder" d="${onTop(pad, top)}"/>` + L(onTop(pad, top), { tone: "lo" }) +
      S_(box(x - PIN / 2, x + PIN / 2, cy - PIN / 2, cy + PIN / 2, top, top + 1.2), { tone: "mid", crease: "none" });
  }).join("");
}
function plugBoard(b, holes) {
  const inner = holes.map(([x, y]) => L(onTop(circle(x, y, 1.25), b.z1), { tone: "lo" })).join("");
  let svg = S_(k.slabOf(plan(b), b.z0 * S, (b.z1 - b.z0) * S, P, 6, 0.6), { tone: "mid", inner });
  svg += holes.map(([x, y]) => `<path class="lp-hole" d="${onTop(circle(x, y, 1.25), b.z1)}"/>` + L(onTop(circle(x, y, 1.25), b.z1), { tone: "lo" }) + L(onTop(circle(x, y, 1.9), b.z1), { tone: "faint" })).join("");
  return svg;
}
// A component box on a board top; small parts get thinner lines.
function compBox(bb, { tone, g, r = 0.08, inner = "" } = {}) {
  const small = Math.max(bb[1] - bb[0], bb[3] - bb[2]) < 1.3;
  const svg = S_(box(bb[0], bb[1], bb[2], bb[3], bb[4], bb[5], { r, steps: 2 }), { tone: tone || (small ? "lo" : "mid"), crease: small ? "none" : "faint", inner });
  return g ? wrap(g, svg) : svg;
}
const holeRing = (x, y, z, r) => `<path class="lp-hole" d="${onTop(circle(x, y, r), z)}"/>` + L(onTop(circle(x, y, r), z), { tone: "lo" });

function feather() {
  const top = FEATHER.z1;
  const comps = compsOf("6000 Feather RP2350", (key) => key === "Board001").filter((c) => c.bb[5] > top + 0.08);
  const items = comps.map((c) => {
    const bb = [...c.bb];
    bb[4] = Math.max(bb[4], top);
    let svg;
    if (c.key.startsWith("QFN60")) {
      svg = wrap("rp2350", compBox(bb, { tone: "hi" }) + D([at([bb[0] + 0.8, bb[3] - 0.8, bb[5]])], { size: 0.5, tone: "lo" }));
    } else if (c.key.startsWith("USB_C")) {
      // Mouth: a recessed stadium in the +x face (measure_feather.json).
      const mouth = stadium([40.89 - 2.865, 14.67], [40.89 + 2.865, 14.67], 2.91).map(([y, z]) => [62.21, y, z]);
      svg = wrap("usbc", S_(box(bb[0], bb[1], bb[2], bb[3], bb[4], bb[5], { r: 0.6, steps: 3 }), { tone: "mid" }) + `<path class="lp-hole" d="${poly(mouth)}"/>` + L(poly(mouth), { tone: "mid" }));
    } else if (c.key.startsWith("JST_SH4")) {
      const mouth = rect(21.22, 26.32, 40.05, 42.35);
      svg = wrap("qt", compBox(bb, { tone: "mid" }) + `<path class="lp-hole" d="${onTop(mouth, bb[5])}"/>` + L(onTop(mouth, bb[5]), { tone: "lo" }));
    } else if (c.key.startsWith("JSTPH2_BATT")) {
      const bodyBB = [46.14, 54.04, 29.9, 37.5, top, 17.865];
      const slot = rect(47.0, 53.2, 31.0, 36.4);
      svg = wrap("jstph", compBox(bodyBB, { tone: "mid" }) + `<path class="lp-hole" d="${onTop(slot, 17.865)}"/>` + L(onTop(slot, 17.865), { tone: "lo" }));
    } else if (c.key.startsWith("BTN_RKB2")) {
      const cx = (bb[0] + bb[1]) / 2, cy = (bb[2] + bb[3]) / 2;
      svg = compBox([bb[0], bb[1], bb[2], bb[3], top, top + 1.5]) + S_(k.cylinder(cx * S, -cy * S, 0.95 * S, (top + 1.5) * S, (bb[5] - top - 1.5) * S, P, 18), { tone: "mid" });
    } else if (c.key.startsWith("FPC_22PIN")) {
      svg = compBox(bb, { inner: L(onTop([[bb[0] + 1.2, bb[2] + 0.4], [bb[0] + 1.2, bb[3] - 0.4]], bb[5], false), { tone: "faint" }) });
    } else {
      svg = compBox(bb);
    }
    return { key: centre(bb), svg };
  });
  const holes = [[2.54, 2.54], [2.54, 20.32], [48.26, 2.54], [48.26, 20.32]].map(([u, v]) => [FEATHER.x0 + u, FEATHER.y0 + v]);
  const tails = HEADERS.feather.map((ref) => pinTails(ref, top)).join("");
  return HEADERS.feather.map(headerPlastic).join("") + wrap("feather", plugBoard(FEATHER, holes)) + tails +
    farFirst(items, (i) => i.key).map((i) => i.svg).join("");
}

function tlv() {
  const top = TLV.z1;
  const comps = compsOf("6309 TLV320DAC3100 I2S DAC", (key) => key === "Board" || key.startsWith("PJ-332A")).filter((c) => c.bb[5] > top + 0.08);
  const items = comps.map((c) => {
    const bb = [...c.bb];
    bb[4] = Math.max(bb[4], top);
    if (c.key.startsWith("TLV320DAC")) return { key: centre(bb), svg: wrap("dac", compBox(bb, { tone: "hi" }) + D([at([bb[0] + 0.6, bb[3] - 0.6, bb[5]])], { size: 0.5, tone: "lo" })) };
    if (c.key.startsWith("JSTPH")) {
      const bodyBB = [52.99, 60.59, 6.58, 14.48, top, 17.865];
      return { key: centre(bodyBB), svg: compBox(bodyBB, { inner: L(onTop([[53.6, 7.2], [53.6, 13.9]], 17.865, false), { tone: "faint" }) }) };
    }
    return { key: centre(bb), svg: compBox(bb) };
  });
  // PJ-332A headphone jack (measure_tlv.json): body on the board, barrel out past the
  // east edge, mouth centre y 18.27 z 15.36, 5.0 barrel, 3.5 mm plug.
  const F = G.frameAlong(W3([59.9, 18.27, 15.36]), [1, 0, 0]);
  const jack = S_(box(48.8, 59.9, 15.07, 21.47, top, 18.07, { r: 0.3, bevel: 0.3 }), { tone: "mid", inner: L(k.rise([57.4 * S, -15.07 * S], top * S, 18.07 * S, P), { tone: "faint" }) }) +
    S_(G.disc(0, 2.9 * S, 2.5 * S, F, P), { tone: "mid" }) +
    `<path class="lp-hole" d="${G.circleOf(F, 2.9 * S, 1.75 * S, P)}"/>` + L(G.circleOf(F, 2.9 * S, 1.75 * S, P), { tone: "mid" });
  items.push({ key: [55, 18.27, 15.5], svg: wrap("jack", jack) });
  const holes = [[2.54, 2.54], [2.54, 22.86], [29.21, 2.54], [29.21, 22.86]].map(([u, v]) => [TLV.x0 + u, TLV.y0 + v]);
  const tails = HEADERS.tlv.map((ref) => pinTails(ref, top)).join("");
  return HEADERS.tlv.map(headerPlastic).join("") + wrap("tlv", plugBoard(TLV, holes)) + tails +
    farFirst(items, (i) => i.key).map((i) => i.svg).join("");
}

function eyespi() {
  const top = EYE.z1;
  const tails = HEADERS.eye.map((ref) => pinTails(ref, top)).join("");
  // 18-pin FPC connector, mouth north toward the top edge: body plus its latch bar.
  const fpc = S_(box(23.88, 37.18, 62.386, 68.136, top, 14.845, { r: 0.15, bevel: 0.2 }), {
    tone: "mid",
    inner: L(onTop([[23.88, 66.9], [37.18, 66.9]], 14.845, false), { tone: "lo" }),
  });
  return HEADERS.eye.map(headerPlastic).join("") + wrap("eyespi", plugBoard(EYE, []) + tails + fpc);
}

// ---- LiPo pouch ----
function battery() {
  const b = { ...BATT, r: 2.0 };
  const pl = plan(b);
  const inner = [
    L(k.planOutline(k.insetPlan(pl, 2.6 * S), b.z1 * S, P, 6), { tone: "faint" }),
    L(k.sideSeam(k.insetPlan(pl, 0), (b.z0 + 1.2) * S, P, 6), { tone: "faint" }),
  ].join("");
  const label = [0, 1, 2].map((i) => L(onTop([[20, 52 - i * 2.4], [i === 1 ? 34 : 41, 52 - i * 2.4]], b.z1, false), { tone: "lo", free: true })).join("");
  return wrap("battery", S_(k.slabOf(pl, b.z0 * S, (b.z1 - b.z0) * S, P, 8, 1.2), { tone: "mid", inner }) + label);
}

// ---- the two parts that swing open, as convex solids in their folded frame ----
// item: { V, F, tone, layer, g, decals: [{ pts, n, kind: "line"|"hole", tone, closed, free }] }
const box3 = (x0, x1, y0, y1, z0, z1) => pbPrism(rect(x0, x1, y0, y1), z0, z1);
function displayItems() {
  const items = [];
  const pcbRing = pbRoundRect(0.04, 61.01, 36.74, 76.11, 2.5, 4);
  const holes = [[2.59, 39.28], [2.59, 73.57], [58.47, 39.28], [58.47, 73.57]];
  const ringAt = (x, y, z, r) => circle(x, y, r, 20).map(([a, b]) => [a, b, z]);
  items.push({ ...pbPrism(pcbRing, -11.085, -9.515), tone: "mid", layer: 1, g: "display", decals: [
    ...holes.map(([x, y]) => ({ pts: ringAt(x, y, -9.515, 1.25), n: [0, 0, 1], kind: "hole" })),
    ...holes.map(([x, y]) => ({ pts: ringAt(x, y, -11.085, 1.25), n: [0, 0, -1], kind: "hole" })),
  ] });
  // Glass on the outer face, with the active area and a now-playing screen on it.
  const zg = -12.631, aa = [3.483, 52.467, 44.407, 68.570];
  const flatRect = (x0, x1, y0, y1) => rect(x0, x1, y0, y1).map(([x, y]) => [x, y, zg]);
  const bar = (x0, x1, y) => ({ pts: [[x0, y, zg], [x1, y, zg]], n: [0, 0, -1], kind: "line", tone: "mid", closed: false, free: true });
  items.push({ ...box3(1.034, 60.216, 41.897, 71.132, -12.631, -11.081), tone: "mid", layer: 0, g: "glass", decals: [
    { pts: flatRect(...aa), n: [0, 0, -1], kind: "line", tone: "lo", closed: true },
    { pts: flatRect(6.5, 15.5, 54.2, 65.2), n: [0, 0, -1], kind: "line", tone: "mid", closed: true },
    bar(19, 44, 63.6), bar(19, 36, 60.8), bar(19, 40, 58.0),
    { pts: flatRect(6.5, 49.5, 48.6, 49.8), n: [0, 0, -1], kind: "line", tone: "lo", closed: true },
    { pts: flatRect(6.5, 31.0, 48.6, 49.8), n: [0, 0, -1], kind: "ink", closed: true },
  ] });
  const comps = compsOf("6366 2.13in Tri-Color eInk", (key) => key === "Board002" || key.startsWith("EINK_213IN"));
  for (const c of comps) {
    const bb = [...c.bb];
    bb[4] = -9.515;
    if (Math.max(bb[1] - bb[0], bb[3] - bb[2]) < 0.9) continue;
    const g = c.key.startsWith("MICROSD") ? "sd" : c.key.startsWith("EYE_SPI") ? "eyespi-socket" : "display";
    const decals = c.key.startsWith("MICROSD") ? [0, 1, 2, 3, 4].map((i) => ({ pts: [[bb[0] + 1.5, bb[2] + 2 + i * 2.4, bb[5]], [bb[1] - 1.5, bb[2] + 2 + i * 2.4, bb[5]]], n: [0, 0, 1], kind: "line", tone: "faint", closed: false })) : [];
    items.push({ ...box3(bb[0], bb[1], bb[2], bb[3], bb[4], bb[5]), tone: Math.max(bb[1] - bb[0], bb[3] - bb[2]) < 1.3 ? "lo" : "mid", layer: 2, g, decals });
  }
  // The panel's own flex tail wraps the east edge from the glass into the 24-pin socket.
  const tail = [[60.2, -11.9], [61.5, -11.9], [62.05, -11.4], [62.05, -9.3], [61.5, -8.9], [53.1, -8.9]];
  items.push({ ribbon: tail.map(([x, z]) => [x, z]), y0: 49.0, y1: 62.4, axis: "y", tone: "mid", layer: 3, g: "display" });
  return items;
}

function neokeyItems() {
  const items = [];
  const ringAt = (x, y, z, r) => circle(x, y, r, 20).map(([a, b]) => [a, b, z]);
  const holes = [[11.48, 10.14], [11.48, 26.65], [49.58, 10.14], [49.58, 26.65]];
  items.push({ ...pbPrism(pbRoundRect(-7.57, 68.63, 7.6, 29.19, 1.5, 3), -12.115, -10.545), tone: "mid", layer: 3, g: "neokey", decals: [
    ...holes.map(([x, y]) => ({ pts: ringAt(x, y, -10.545, 1.25), n: [0, 0, 1], kind: "hole" })),
    ...holes.map(([x, y]) => ({ pts: ringAt(x, y, -12.115, 1.25), n: [0, 0, -1], kind: "hole" })),
  ] });
  for (const [cx, cy] of KEYS) {
    const f = NK_FACE;
    items.push({ ...pbFrustum(cx, cy, 14.0, 14.0, f, 14.0, 14.0, f - 5.0), tone: "mid", layer: 2, g: "keys", decals: [] });
    items.push({ ...pbFrustum(cx, cy, 15.6, 15.6, f - 5.0, 12.0, 12.0, f - 11.6), tone: "mid", layer: 1, g: "keys", decals: [] });
    const dish = rect(cx - 5.2, cx + 5.2, cy - 5.2, cy + 5.2).map(([x, y]) => [x, y, f - 21.5]);
    items.push({ ...pbFrustum(cx, cy, 18.2, 18.2, f - 12.4, 13.0, 13.0, f - 21.5), tone: "hi", layer: 0, g: "keys", decals: [
      { pts: dish, n: [0, 0, -1], kind: "line", tone: "faint", closed: true },
    ] });
  }
  const comps = compsOf("4980 NeoKey 1x4 QT", (key) => key === "Board003");
  for (const c of comps) {
    const bb = [...c.bb];
    bb[4] = -10.545;
    if (bb[5] <= -10.5 || Math.max(bb[1] - bb[0], bb[3] - bb[2]) < 0.9) continue;
    const g = c.key.startsWith("JST_SH") ? "nk-qt" : "neokey";
    items.push({ ...box3(bb[0], bb[1], bb[2], bb[3], bb[4], bb[5]), tone: "mid", layer: 4, g, decals: [] });
  }
  return items.concat(anoItems());
}

// The ANO moves with the NeoKey (same frame), as its own object for depth order.
function anoItems() {
  const items = [];
  const { cx, cy, zf, zb } = ANO;
  const ringAt = (x, y, z, r, n = 20) => circle(x, y, r, n).map(([a, b]) => [a, b, z]);
  const up = [0, 0, -1];
  const holes = [[-17.78, -15.24], [-17.78, 15.24], [17.78, -15.24], [17.78, 15.24]].map(([dx, dy]) => [cx + dx, cy + dy]);
  items.push({ ...pbPrism(pbRoundRect(ANO.x0, ANO.x1, ANO.y0, ANO.y1, 2.54, 4), zf, zb), tone: "mid", layer: 4, g: "ano", decals: [
    ...holes.map(([x, y]) => ({ pts: ringAt(x, y, zf, 1.25), n: up, kind: "hole" })),
    ...holes.map(([x, y]) => ({ pts: ringAt(x, y, zb, 1.25), n: [0, 0, 1], kind: "hole" })),
  ] });
  // Encoder: square body on the PCB, a 34 mm bezel plate, the ring with its four
  // direction buttons, and the turning wheel with the centre button.
  items.push({ ...box3(cx - 16, cx + 16, cy - 16, cy + 16, -23.745, zf), tone: "mid", layer: 3, g: "ano", decals: [] });
  items.push({ ...box3(cx - 17, cx + 17, cy - 17, cy + 17, -24.345, -23.745), tone: "mid", layer: 2, g: "ano", decals: [] });
  const arrows = [[0, 1], [1, 0], [0, -1], [-1, 0]].map(([ux, uy]) => {
    const r = 14.8, w = 1.1, t = [cx + ux * (r + 1.1), cy + uy * (r + 1.1)];
    const a = [cx + ux * (r - 0.6) - uy * w, cy + uy * (r - 0.6) + ux * w], b = [cx + ux * (r - 0.6) + uy * w, cy + uy * (r - 0.6) - ux * w];
    return { pts: [a, t, b].map(([x, y]) => [x, y, -27.345]), n: up, kind: "line", tone: "mid", closed: true };
  });
  items.push({ ...pbPrism(circle(cx, cy, 17.15, 36), -27.345, -24.345), tone: "mid", layer: 1, g: "ano", decals: arrows });
  items.push({ ...pbPrism(circle(cx, cy, 12.45, 32), -27.545, -27.345), tone: "hi", layer: 0, g: "ano-wheel", decals: [
    { pts: ringAt(cx, cy, -27.545, 4.33, 24), n: up, kind: "line", tone: "mid", closed: true },
    { pts: ringAt(cx, cy, -27.545, 10.6, 32), n: up, kind: "line", tone: "faint", closed: true },
  ] });
  // Parts on its back, toward the board: the seesaw ATtiny and two STEMMA QT sockets.
  for (const c of compsOf("5740 ANO Rotary Encoder QT", (key) => key.startsWith("ENCODER_ANO"))) {
    const bb = [...c.bb];
    bb[4] = zb;
    if (bb[5] <= zb + 0.05 || Math.max(bb[1] - bb[0], bb[3] - bb[2]) < 0.9) continue;
    const g = c.key.startsWith("STEMMA") ? "ano-qt" : "ano";
    items.push({ ...box3(bb[0], bb[1], bb[2], bb[3], bb[4], bb[5]), tone: c.key.startsWith("QFN20") ? "hi" : "mid", layer: 5, g, decals: [] });
  }
  return items.map((it) => ({ ...it, obj: "ano" }));
}

// ---- flex: the EYESPI cable from the breakout's FPC socket over the top edge ----
const FLEX = {
  x0: 24.68, x1: 36.38,                                    // 13.3 mm sockets, 0.8 in each side
  top: [[68.136, 14.0], [69.4, 15.1], [75.4, 15.1]],        // breakout frame (y, z), runs over the pins
  bot: [[75.9, -8.6], [73.0, -8.6]],                        // display frame, into its socket mouth
};

// ---- assemble the static art ----
const sockets = [
  socket("J1", "j-feather"), socket("J2", "j-feather"),
  socket("J9", "j-tlv"), socket("J10", "j-tlv"),
  socket("J4", "j-eyespi"), socket("J5", "j-eyespi"),
  jumper("R1"), jumper("R2"), jumper("R3"), jumper("R4"),
  slideSwitch(),
];
const pins = Object.values(HEADERS).flat().map(headerPins).join("");

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label:
    "The E-ink Audio Player, a palm-sized RP2350 music player. A 61 by 76 mm milled single-sided board carries a Feather RP2350, a TLV320DAC3100 DAC with a headphone jack and an EYESPI breakout on SMT sockets; a flex folds over the top edge to a 2.13 inch e-ink on the back, beside a 2000 mAh LiPo and a NeoKey 1x4, with an ANO rotary encoder for the thumb past the end of the keys. It sits as on its stand, seen from behind: the board at 65 degrees, the keys in front at 10 degrees and the ANO past their right end. Taken apart, the boards lift off their sockets, the e-ink swings open on its flex, the LiPo drops, and the keys and the ANO slide out together to the side, while each function lights up in turn.",
  body: [
    `<g transform="${POSE}">`,
    `<g data-part="k-back"></g>`,
    `<g data-part="display"></g>`,
    `<g data-part="flex-back"></g>`,
    `<g data-ride="battery">${battery()}</g>`,
    wrap("pad", padBoard()),
    `<g data-part="copper">${copper()}</g>`,
    `<g data-part="pulses"></g>`,
    `<g data-ride="top">${pins}</g>`,
    farFirst(sockets, (s) => s.key).map((s) => s.svg).join(""),
    `<g data-ride="top">${eyespi()}</g>`,
    `<g data-part="flex-front"></g>`,
    `<g data-ride="top">${feather()}</g>`,
    `<g data-ride="top">${tlv()}</g>`,
    `<g data-part="k-front"></g>`,
    `</g>`,
  ],
});

const CSS = `<style>
.lp-groove{fill:var(--anatomy-shade-0);stroke:none}
.lp-cu-fill{fill:var(--anatomy-top);stroke:none}
.lp-hole{fill:var(--anatomy-paper);stroke:none}
.lp-solder{fill:var(--anatomy-shade-1);stroke:none}
.lp-ink{fill:var(--anatomy-mid);stroke:none}
[data-on] .lp-ink{fill:var(--anatomy-lit)}
.lp-cu-edge{stroke-width:.55px}
[data-net][data-on] .lp-cu-fill{fill:var(--anatomy-lit-top)}
[data-net][data-on] .lp-cu-edge{stroke:var(--anatomy-lit);stroke-width:1.1px}
.iso-solid[data-lit]>.iso-edge{stroke-width:1.1px}
.lp-dot{fill:var(--anatomy-lit)}
</style>`;

// ---- tour ----
// Each step: what lights up, the readout, and the pose (apart, display angle).
const STEPS = [
  { read: "RP2350 music player · milled E-ink Audio Player board, 61 × 76 mm", apart: 0, d: 1, g: [], nets: [] },
  { read: "Board · single-sided F.Cu, 0.4 mm traces, GND fill, R1–R4 0R hops", apart: 1, d: 1, g: ["pad", "jumper"], nets: [] },
  { read: "Power · LiPo 2000 mAh → Feather JST · SW1 grounds EN = off · 3V3 rail", apart: 1, d: 1, g: ["battery", "jstph", "usbc", "sw1"], nets: ["3V3", "EN"] },
  { read: "Brain · Feather RP2350 on J1 + J2, 14 pins used", apart: 1, d: 1, g: ["feather", "rp2350", "j-feather"], nets: [] },
  { read: "Storage · microSD on the e-ink board · SPI + SDCS (D24)", apart: 1, d: 0.5, g: ["sd", "eyespi", "flex", "eyespi-socket", "j-eyespi"], nets: ["SCK", "MOSI", "MISO", "SD_CS"] },
  { read: "Display · EYESPI flex → 2.13in e-ink · DC, RST, TCS, BUSY", apart: 1, d: 1, g: ["glass", "display", "eyespi", "flex", "eyespi-socket", "j-eyespi"], nets: ["SCK", "MOSI", "EPD_DC", "EPD_RST", "EPD_TCS", "EPD_BUSY"] },
  { read: "Audio · I2S A0 A1 A2 hop 3V3 on R3 R2 R1 → TLV320DAC3100 → jack", apart: 1, d: 1, g: ["tlv", "dac", "jack", "j-tlv", "r1", "r2", "r3"], nets: ["I2S_BCLK", "I2S_WSEL", "I2S_DIN", "SDA", "SCL"] },
  { read: "Controls · NeoKey 1x4, four MX keys · STEMMA QT I2C", apart: 1, d: 1, g: ["neokey", "keys", "qt", "nk-qt"], nets: [] },
  { read: "Thumb · ANO wheel + 5 buttons on the stand · chained STEMMA QT, I2C 0x49", apart: 1, d: 1, g: ["ano", "ano-wheel", "ano-qt", "nk-qt"], nets: [] },
];
const STEP_MS = 3400;
const TOUR_MS = STEPS.length * STEP_MS;

const live = `
${readFileSync(join(HERE, "poly.mjs"), "utf8").replace(/^import .*$/m, "").replace(/^const \{ iso, pathOf, cameraOf \} = await import.*$/m, "").replace(/^export /gm, "")}
window.__anatomy = { tourMs: ${TOUR_MS} };
const P = ${JSON.stringify(P)};
const S = ${S}, LIFT = ${LIFT}, DROP = ${DROP}, STEP_MS = ${STEP_MS};
const D_HINGE = ${JSON.stringify(D_HINGE)}, K_A = ${K_A}, K_T = ${JSON.stringify(K_T)}, K_OUT = ${JSON.stringify(K_OUT)};
const FLEX = ${JSON.stringify(FLEX)};
const STEPS = ${JSON.stringify(STEPS)};
const DISPLAY = ${JSON.stringify(displayItems())};
const NEOKEY = ${JSON.stringify(neokeyItems())};
const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const part = (name) => svg.querySelector('[data-part="' + name + '"]');
const rides = (name) => [...svg.querySelectorAll('[data-ride="' + name + '"]')];
const topG = rides("top"), battG = rides("battery");
const readout = document.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const ease = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
const cam = pbCam(P);
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

const rot = ([x, y, z], [hy, hz], a) => {
  const c = Math.cos(a), s = Math.sin(a), dy = y - hy, dz = z - hz;
  return [x, hy + dy * c - dz * s, hz + dy * s + dz * c];
};
const W = (p) => [p[0] * S, -p[1] * S, p[2] * S];
const Wn = (n) => [n[0], -n[1], n[2]];
let lit = new Set();

// A flat ribbon along a polyline in one plane, drawn quad by quad, far first.
function ribbon(pts3, across, tone, g) {
  const quads = [];
  for (let i = 0; i + 1 < pts3.length; i++) {
    const a = pts3[i], b = pts3[i + 1];
    const q = [W([a[0] + across[0][0], a[1] + across[0][1], a[2] + across[0][2]]), W([b[0] + across[0][0], b[1] + across[0][1], b[2] + across[0][2]]),
      W([b[0] + across[1][0], b[1] + across[1][1], b[2] + across[1][2]]), W([a[0] + across[1][0], a[1] + across[1][1], a[2] + across[1][2]])];
    const u = [q[1][0] - q[0][0], q[1][1] - q[0][1], q[1][2] - q[0][2]], v = [q[3][0] - q[0][0], q[3][1] - q[0][1], q[3][2] - q[0][2]];
    let n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const l = Math.hypot(...n) || 1;
    n = n.map((c) => c / l);
    if (dot(n, cam.V) < 0) n = n.map((c) => -c);
    const c = q.reduce((s, p) => [s[0] + p[0] / 4, s[1] + p[1] / 4, s[2] + p[2] / 4], [0, 0, 0]);
    quads.push({ q, band: pbBand(dot(n, cam.L)), depth: depthOf(c, P), i });
  }
  quads.sort((a, b) => a.depth - b.depth);
  const on = lit.has(g);
  return '<g data-g="' + g + '"' + (on ? " data-on" : "") + '>' + quads.map(({ q, band, i }) => {
    const p = q.map((w) => iso(w, P));
    const d = pathOf(p, true);
    const cls = band === 4 ? '<path class="iso-top" d="' + d + '"/>' : '<path class="iso-shade" data-shade="' + band + '" d="' + d + '"/>';
    const edges = pathOf([p[0], p[1]]) + pathOf([p[3], p[2]]) + (i === 0 ? pathOf([p[0], p[3]]) : "") + (i === pts3.length - 2 ? pathOf([p[1], p[2]]) : "");
    return '<g class="iso-solid" data-seamless' + (on ? " data-lit" : "") + '><path class="iso-fill" d="' + d + '"/>' + cls +
      '<path class="iso-line iso-edge" data-tone="' + tone + '" d="' + edges + '"/></g>';
  }).join("") + "</g>";
}

// The swinging parts, rebuilt for an angle.
function swing(items, hinge, a, off = [0, 0, 0]) {
  const R = (p) => { const q = rot(p, hinge, a); return [q[0] + off[0], q[1] + off[1], q[2] + off[2]]; };
  const inner = Wn([0, -Math.sin(a), Math.cos(a)]);
  const innerSeen = dot(inner, cam.V) > 0;
  const list = items.map((it) => {
    if (it.ribbon) {
      const pts = it.ribbon.map(([x, z]) => R([x, (it.y0 + it.y1) / 2, z]));
      const h = (it.y1 - it.y0) / 2, off = rot([0, h, 0], [0, 0], a), off2 = rot([0, -h, 0], [0, 0], a);
      const c = pts[Math.floor(pts.length / 2)];
      return { obj: it.obj || "", layer: it.layer, depth: depthOf(W(c), P), html: () => ribbon(pts, [off2, off], it.tone, it.g) };
    }
    const V = it.V.map((p) => W(R(p)));
    const c = V.reduce((s, p) => [s[0] + p[0] / V.length, s[1] + p[1] / V.length, s[2] + p[2] / V.length], [0, 0, 0]);
    return { obj: it.obj || "", layer: it.layer, depth: depthOf(c, P), html: () => {
      const on = lit.has(it.g);
      let out = solidSvg(polyPaths(V, it.F, P), { tone: it.tone, crease: "faint", lit: on });
      for (const dc of it.decals) {
        const n = Wn(rot(dc.n, [0, 0], a));
        if (dot(n, cam.V) <= 1e-6) continue;
        const pts = dc.pts.map((p) => iso(W(R(p)), P));
        if (dc.kind === "hole") out += '<path class="lp-hole" d="' + pathOf(pts, true) + '"/>' + lineSvg(pathOf(pts, true), { tone: "lo" });
        else if (dc.kind === "ink") out += '<path class="lp-ink" d="' + pathOf(pts, true) + '"/>';
        else out += lineSvg(pathOf(pts, dc.closed), { tone: on && dc.tone === "mid" ? "hi" : dc.tone, free: dc.free });
      }
      return '<g data-g="' + it.g + '"' + (on ? " data-on" : "") + '>' + out + "</g>";
    } };
  });
  const od = {};
  for (const it of list) (od[it.obj] = od[it.obj] || []).push(it.depth);
  for (const o in od) od[o] = od[o].reduce((a, b) => a + b, 0) / od[o].length;
  list.sort((p, q) => (p.obj !== q.obj ? od[p.obj] - od[q.obj] : 0) ||
    (innerSeen ? p.layer - q.layer : q.layer - p.layer) || p.depth - q.depth);
  return list.map((it) => it.html()).join("");
}

// The flex: a run on the breakout, a free bend, and a run into the display's socket.
function bez(p0, p1, p2, p3, n) {
  const out = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, u = 1 - t;
    out.push([0, u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0], u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]]);
  }
  return out;
}
function flex(lift, a) {
  const top = FLEX.top.map(([y, z]) => [0, y, z + lift]);
  const r1 = top[top.length - 1];
  const bot = FLEX.bot.map(([y, z]) => rot([0, y, z], D_HINGE, a));
  const r2 = bot[0];
  const dir = rot([0, 1, 0], [0, 0], a); // leaving the display run toward the bend
  const dist = Math.hypot(r2[1] - r1[1], r2[2] - r1[2]);
  const t = 1.5 + 0.12 * dist;
  const curve = bez([r1[1], r1[2]], [r1[1] + t, r1[2]], [r2[1] + dir[1] * t, r2[2] + dir[2] * t], [r2[1], r2[2]], 22).map(([, y, z]) => [0, y, z]);
  const innerSeen = dot(Wn([0, -Math.sin(a), Math.cos(a)]), cam.V) > 0;
  const back = innerSeen ? curve.concat(bot.slice(1)) : curve;
  const across = [[FLEX.x0, 0, 0], [FLEX.x1, 0, 0]];
  return { front: ribbon(top, across, "mid", "flex"), back: ribbon(back, across, "mid", "flex") };
}

// ---- state ----
let step = 0, u = 0, dm = 1, clock = 0, touring = !still.matches, visible = false, frame = 0, last = 0, idle = 0;
let target = { apart: 0, d: 1 };
let shownKey = "", shownStep = -1;

function select(i) {
  if (i === shownStep) return;
  shownStep = i;
  const s = STEPS[i];
  lit = new Set(s.g);
  const nets = new Set(s.nets);
  svg.querySelectorAll("[data-net]").forEach((el) => el.toggleAttribute("data-on", nets.has(el.dataset.net)));
  svg.querySelectorAll("[data-g]").forEach((el) => {
    const on = el.dataset.g.split(" ").some((g) => lit.has(g));
    el.toggleAttribute("data-on", on);
    el.querySelectorAll(".iso-solid").forEach((x) => x.toggleAttribute("data-lit", on));
  });
  shownKey = "";
  if (readout.textContent !== s.read) readout.textContent = s.read;
  stage.setAttribute("aria-valuetext", s.read);
}

function draw() {
  const lift = LIFT * ease(u / 0.45);
  const mK = ease((u - 0.15) / 0.6);
  const aD = Math.PI * ease((u - 0.25) / 0.6) * dm;
  const drop = DROP * ease((u - 0.6) / 0.4);
  const mv = (list, v) => list.forEach((g) => (v[2] ? g.setAttribute("transform", translateAlong(P, v)) : g.removeAttribute("transform")));
  mv(topG, [0, 0, lift * S]);
  mv(battG, [0, 0, -drop * S]);
  const key = lift.toFixed(2) + ":" + mK.toFixed(3) + ":" + aD.toFixed(3) + ":" + shownStep;
  if (key !== shownKey) {
    shownKey = key;
    const kOut = mK > 0.5;
    const kHtml = swing(NEOKEY, [0, 0], K_A, K_T.map((v, i) => v + K_OUT[i] * mK));
    part("k-back").innerHTML = kOut ? "" : kHtml;
    part("k-front").innerHTML = kOut ? kHtml : "";
    part("display").innerHTML = swing(DISPLAY, D_HINGE, aD);
    const f = flex(lift, aD);
    part("flex-back").innerHTML = f.back;
    part("flex-front").innerHTML = f.front;
  }
}

function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  if (touring) {
    clock += dt;
    const i = Math.floor((clock * 1000) / STEP_MS) % STEPS.length;
    select(i);
    target = STEPS[i];
  }
  const k = 1 - Math.exp(-dt / 0.5);
  u = still.matches ? target.apart : u + (target.apart - u) * k;
  dm = still.matches ? target.d : dm + (target.d - dm) * k;
  if (Math.abs(target.apart - u) < 0.001) u = target.apart;
  if (Math.abs(target.d - dm) < 0.001) dm = target.d;
  draw();
  const settled = !touring && u === target.apart && dm === target.d;
  frame = visible && !settled ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
const hold = () => { touring = false; clearTimeout(idle); idle = setTimeout(() => { touring = !still.matches; clock = shownStep * STEP_MS / 1000; run(); }, 5000); run(); };
const pick = (i) => { select(i); target = { apart: STEPS[i].apart || (shownStep ? 1 : 0), d: STEPS[i].d }; hold(); };
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
stage.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") { target = { ...target, apart: 1 }; if (!shownStep) select(1); hold(); } });
stage.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") { target = { apart: 0, d: 1 }; select(0); hold(); } });
stage.addEventListener("click", (e) => { if (e.pointerType !== "mouse") pick(shownStep ? 0 : 1); });
stage.addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight" || e.key === "ArrowDown") pick((shownStep + 1) % STEPS.length);
  else if (e.key === "ArrowLeft" || e.key === "ArrowUp") pick((shownStep + STEPS.length - 1) % STEPS.length);
  else return;
  e.preventDefault();
});
select(0);
draw();
`;

const body = CSS + k.plateHtml({
  fig: "Fig 1",
  title: "E-ink Audio Player",
  hint: hero ? "" : "Hover to take apart · ← → step through",
  readout: STEPS[0].read,
  keys: [
    { mark: "lit", label: "The function in the readout: its traces, pads and parts" },
    { mark: "raised", label: "Feather RP2350, TLV320DAC3100, EYESPI on top; LiPo, e-ink, NeoKey 1x4 on the back" },
  ],
  caption:
    "A 61.06 × 76.16 mm board milled from single-sided copper: 0.4 mm traces, a GND fill, and four 0805 0R jumpers where a trace has to hop another. Adafruit boards plug into SMT sockets; the EYESPI flex wraps the top edge to the e-ink. The LiPo and STEMMA QT cables are not drawn.",
  body: `<div class="iso-stage" tabindex="0" role="group" aria-roledescription="interactive figure" aria-label="E-ink audio player: arrow keys step through the functions, hover takes it apart">${svg}</div>`,
});

const name = `eink-audio-player${hero ? "-hero" : ""}${theme === "light" ? "-light" : ""}.html`;
mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, name), k.pageHtml({ title: "E-ink Audio Player", theme, body, script: kitScript() + live }));
console.log("wrote", name);
