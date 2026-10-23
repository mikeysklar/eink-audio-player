// Convex solids at any orientation, shaded the way the kit shades its prisms
// (lathe.mjs prismOf: four side tones by light, a top tone, hull fill and outline).
// The page inlines this file after the kit, so the display and the NeoKey can be
// rebuilt every frame while they swing open.
import { KIT } from "./kit-dir.mjs";
const { iso, pathOf, cameraOf } = await import(`${KIT}/kit/iso-kit.mjs`);

const PB_BANDS = [0, 0.2, 0.42, 0.62];
export function pbBand(score) {
  let tone = 0;
  while (tone < PB_BANDS.length && score >= PB_BANDS[tone]) tone++;
  return tone;
}
export function pbCam(P) {
  const { sinA, cosA, sinE, cosE } = cameraOf(P);
  const l = Math.hypot(sinA, cosA, 1.2);
  return { V: [cosA * cosE, sinA * cosE, sinE], L: [-sinA / l, cosA / l, 1.2 / l] };
}
const pbDot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export function pbHull(points) {
  const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (p.length < 3) return p;
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [], upper = [];
  for (const q of p) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop(); lower.push(q); }
  for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop(); upper.push(q); }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}
// Newell normal of a face, turned to point away from the solid's centre.
export function pbNormal(V, face, centre) {
  let n = [0, 0, 0];
  for (let i = 0; i < face.length; i++) {
    const a = V[face[i]], b = V[face[(i + 1) % face.length]];
    n = [n[0] + (a[1] - b[1]) * (a[2] + b[2]), n[1] + (a[2] - b[2]) * (a[0] + b[0]), n[2] + (a[0] - b[0]) * (a[1] + b[1])];
  }
  const l = Math.hypot(n[0], n[1], n[2]) || 1;
  n = [n[0] / l, n[1] / l, n[2] / l];
  const c = face.reduce((s, i) => [s[0] + V[i][0], s[1] + V[i][1], s[2] + V[i][2]], [0, 0, 0]).map((v) => v / face.length);
  return pbDot(n, [c[0] - centre[0], c[1] - centre[1], c[2] - centre[2]]) < 0 ? [-n[0], -n[1], -n[2]] : n;
}
// V: world points (already scaled), F: faces as vertex index lists.
export function polyPaths(V, F, P) {
  const { V: view, L } = pbCam(P);
  const centre = V.reduce((s, p) => [s[0] + p[0], s[1] + p[1], s[2] + p[2]], [0, 0, 0]).map((v) => v / V.length);
  const pts = V.map((p) => iso(p, P));
  const buckets = [[], [], [], [], []];
  const normals = F.map((f) => pbNormal(V, f, centre));
  const seen = normals.map((n) => pbDot(n, view) > 1e-6);
  F.forEach((f, i) => { if (seen[i]) buckets[pbBand(pbDot(normals[i], L))].push(pathOf(f.map((j) => pts[j]), true)); });
  const edges = new Map();
  F.forEach((f, i) => f.forEach((a, j) => {
    const b = f[(j + 1) % f.length];
    const key = a < b ? a + ":" + b : b + ":" + a;
    (edges.get(key) || edges.set(key, []).get(key)).push(i);
  }));
  const creases = [];
  for (const [key, faces] of edges) {
    if (faces.length !== 2 || !seen[faces[0]] || !seen[faces[1]]) continue;
    if (pbDot(normals[faces[0]], normals[faces[1]]) > 0.94) continue;
    const [a, b] = key.split(":").map(Number);
    creases.push(pathOf([pts[a], pts[b]]));
  }
  const hull = pathOf(pbHull(pts), true);
  return { fill: hull, outline: hull, crease: creases.join(""), top: buckets[4].join(""), shades: buckets.slice(0, 4).map((l) => l.join("")) };
}
// A prism: a convex floor ring [[x, y]] from z0 to z1 (all in mm, local frame).
export function pbPrism(ring, z0, z1) {
  const n = ring.length;
  const V = [...ring.map(([x, y]) => [x, y, z0]), ...ring.map(([x, y]) => [x, y, z1])];
  const F = [ring.map((_, i) => i), ring.map((_, i) => n + i)];
  for (let i = 0; i < n; i++) F.push([i, (i + 1) % n, n + (i + 1) % n, n + i]);
  return { V, F };
}
// A frustum between two centred rectangles: w0 x d0 at z0 and w1 x d1 at z1.
export function pbFrustum(cx, cy, w0, d0, z0, w1, d1, z1) {
  const rect = (w, d, z) => [[cx - w / 2, cy - d / 2, z], [cx + w / 2, cy - d / 2, z], [cx + w / 2, cy + d / 2, z], [cx - w / 2, cy + d / 2, z]];
  const V = [...rect(w0, d0, z0), ...rect(w1, d1, z1)];
  const F = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]];
  return { V, F };
}
export function pbRoundRect(x0, x1, y0, y1, r, steps = 4) {
  const out = [];
  const c = [[x1 - r, y0 + r, -90], [x1 - r, y1 - r, 0], [x0 + r, y1 - r, 90], [x0 + r, y0 + r, 180]];
  for (const [cx, cy, a0] of c) for (let i = 0; i <= steps; i++) {
    const a = ((a0 + (90 * i) / steps) * Math.PI) / 180;
    out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  return out;
}
