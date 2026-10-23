# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
"""Mini-arcade stand for the landing pad: the shared frame every part builds in.

Writes layout.json. Plain python3, no FreeCAD.

World frame, mm: the desk is Z=0, Z up. The player sits at -Y looking toward +Y.
X is the player's right. The stand is symmetric about X=0.

Two rigid bodies are placed from the board's own STEP frame (inputs/board.step:
origin at the board outline's bottom-left, Y up the board, the display and battery on
the -Z side, the Feather/TLV/EYESPI on +Z):

  stack  the board with the Feather, TLV, EYESPI, battery and the e-ink. Tilted so the
         e-ink faces the player, SCREEN_DEG from the desk, the board's top edge (the
         flex fold) highest. Board +X runs to the player's LEFT, so the plugs on the
         board's right edge (USB-C, jack, SW1) come out on the player's left.
  keys   the NeoKey 1x4 on its own deck in front, keys up, DECK_DEG from the desk,
         falling toward the player. One STEMMA QT cable joins the two.

A board point p = (x, y, z) goes to world P0 + x*BX + y*BY + z*BZ for each body.
"""

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = os.path.join(HERE, "inputs")

SCREEN_DEG = 65.0
DECK_DEG = 10.0

# The glass plane's bottom edge (board y=0, z=glass) sits here, centred on X=0.
GLASS_Z = -12.631
STACK_ORIGIN = (0.0, 0.0, 16.0)
# NeoKey key face centre (its PCB face, where the switches sit).
KEYS_ORIGIN = (0.0, -16.0, 11.0)

BOARD_CX = 30.53          # board outline centre in X (61.06 / 2)
NK_CX, NK_CY, NK_FACE = 30.53, 18.395, -12.115

# The cheeks: inner faces at +-X_IN, CHEEK_T thick.
X_IN = 39.5
CHEEK_T = 4.0
SCREW = {"m": 2.5, "clear_d": 2.8, "pilot_d": 2.2, "insert_od": 3.6, "head_d": 4.6}


def basis(deg, upslope_sign=1):
    """Body axes for a face tilted deg from the desk, facing the player (-Y) and up.
    BX = player's left (-X world); BY = up the slope; BZ = into the face (away)."""
    t = math.radians(deg)
    bx = (-1.0, 0.0, 0.0)
    by = (0.0, math.cos(t), math.sin(t))
    bz = (0.0, math.sin(t), -math.cos(t))
    return bx, by, bz


def place(origin_world, origin_board, axes):
    """P0 such that origin_board maps to origin_world."""
    bx, by, bz = axes
    ox, oy, oz = origin_board
    return tuple(origin_world[i] - (bx[i] * ox + by[i] * oy + bz[i] * oz) for i in range(3))


def tf(p0, axes, p):
    bx, by, bz = axes
    return [round(p0[i] + bx[i] * p[0] + by[i] * p[1] + bz[i] * p[2], 3) for i in range(3)]


def box_corners(b):
    x0, x1, y0, y1, z0, z1 = b
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def world_bbox(p0, axes, b):
    pts = [tf(p0, axes, c) for c in box_corners(b)]
    return [round(f(p[i] for p in pts), 2) for i in range(3) for f in (min, max)]


def main():
    sa = basis(SCREEN_DEG)
    ka = basis(DECK_DEG)
    s0 = place(STACK_ORIGIN, (BOARD_CX, 0.0, GLASS_Z), sa)
    k0 = place(KEYS_ORIGIN, (NK_CX, NK_CY, NK_FACE), ka)

    parts = json.load(open(os.path.join(CASE, "parts_bbox.json")))
    disp = json.load(open(os.path.join(CASE, "measure_display.json")))
    nk = json.load(open(os.path.join(CASE, "measure_neokey_sw1.json")))
    fe = json.load(open(os.path.join(CASE, "measure_feather.json")))
    tlv = json.load(open(os.path.join(CASE, "measure_tlv.json")))

    stack_parts = {k: v for k, v in parts.items() if not k.startswith("4980")}
    out = {
        "doc": __doc__,
        "screen_deg": SCREEN_DEG, "deck_deg": DECK_DEG,
        "x_in": X_IN, "cheek_t": CHEEK_T, "screw": SCREW,
        "stack": {"p0": s0, "bx": sa[0], "by": sa[1], "bz": sa[2],
                  "normal_to_player": [-c for c in sa[2]]},
        "keys": {"p0": k0, "bx": ka[0], "by": ka[1], "bz": ka[2],
                 "normal_up": [-c for c in ka[2]]},
        "stack_part_bboxes_world": {k: world_bbox(s0, sa, v) for k, v in stack_parts.items()},
        "neokey_bbox_world": world_bbox(k0, ka, parts["4980 NeoKey 1x4 QT"]),
    }
    # Display: glass, active area, its four holes (through display + board, M2.5).
    g = disp["glass"]
    a = disp["active_area"]["bbox"]
    out["display"] = {
        "glass_corners_world": [tf(s0, sa, (x, y, g[4])) for x, y in
                                ((g[0], g[2]), (g[1], g[2]), (g[1], g[3]), (g[0], g[3]))],
        "active_corners_world": [tf(s0, sa, (x, y, a[4])) for x, y in
                                 ((a[0], a[2]), (a[1], a[2]), (a[1], a[3]), (a[0], a[3]))],
        "glass_face_z_board": g[4],
        "pcb_front_z_board": disp["outer_face_z"]["pcb"],
        "holes_world_on_pcb_front": [tf(s0, sa, (x, y, disp["outer_face_z"]["pcb"]))
                                     for x, y in disp["pcb"]["holes"]],
        "note": "Each hole is an M2.5 through the display PCB, lined up with a board hole "
                "(H1-H4) and a brass standoff between display and board. A longer screw "
                "from the front can go through a bezel boss, the display and into the "
                "standoff. Screw heads sit proud of the display PCB front, so a bezel "
                "touching the PCB front needs a 5.5 mm pocket at each hole.",
    }
    # Board holes not used by the display (H5 Feather corner, H6 TLV corner, H7 bottom-left).
    bh = {"H5": (58.47, 49.77), "H6": (58.47, 4.05), "H7": (2.59, 4.05)}
    out["board_holes_world"] = {k: {"on_board_bottom": tf(s0, sa, (x, y, 0.0)),
                                    "on_board_top": tf(s0, sa, (x, y, 1.6)),
                                    "note": "back side: battery is clear of these"}
                                for k, (x, y) in bh.items()}
    # The board's bottom edge (y=0) runs across the stack's lowest front corner.
    out["stack_bottom_edge_world"] = [tf(s0, sa, (0.05, 0.0, 0.0)), tf(s0, sa, (61.01, 0.0, 0.0))]
    out["stack_top_edge_world"] = [tf(s0, sa, (0.05, 76.11, 0.0)), tf(s0, sa, (61.01, 76.11, 0.0))]
    # Ports, all on the player's LEFT (board +X edge). Axis is world -X out of the mouth.
    u = fe["usb_c"]["bbox"]
    j = tlv["jack"]
    sw = nk["sw1"]["knob_bbox"]
    out["ports_world"] = {
        "usb_c": {"mouth": tf(s0, sa, (62.21, 40.89, 14.67)), "axis": [-1, 0, 0],
                  "keepout_d": 14.0, "note": "plug overmold ~12.4 x 6.5; keep the cheek "
                  "clear of a 14 mm circle round this axis"},
        "jack": {"mouth": tf(s0, sa, (62.8, j["mouth_center_yz"][0], j["mouth_center_yz"][1])),
                 "axis": [-1, 0, 0], "keepout_d": 11.0},
        "sw1_knob": {"centre": tf(s0, sa, ((sw[0] + sw[1]) / 2, (sw[2] + sw[3]) / 2,
                                           (sw[4] + sw[5]) / 2)),
                     "axis": [-1, 0, 0], "keepout_d": 9.0, "note": "finger room to slide it"},
        "feather_qt": {"mouth": tf(s0, sa, (23.77, 41.2, 17.36)),
                       "note": "opens away from the board (+Z board = back/down in world); "
                               "the QT cable to the NeoKey leaves here"},
    }
    # Keys: switch centres on the NeoKey face, plate top 5.0 above the face (MX spec),
    # plate 1.5 thick, 14.0 square holes. Keycap top ~21.5 above the face.
    out["keys_world"] = {
        "switch_centres_on_face": [tf(k0, ka, (x, y, NK_FACE)) for x, y in nk["neokey"]["key_centres"]],
        "plate_top_centres": [tf(k0, ka, (x, y, NK_FACE - 5.0)) for x, y in nk["neokey"]["key_centres"]],
        "keycap_top_centres": [tf(k0, ka, (x, y, NK_FACE - 21.5)) for x, y in nk["neokey"]["key_centres"]],
        "plate_thickness": 1.5, "hole": 14.0,
        "neokey_holes_on_face": [tf(k0, ka, (h["x"], h["y"], NK_FACE)) for h in nk["neokey"]["holes"]],
        "neokey_qt": [tf(k0, ka, ((q["bbox"][0] + q["bbox"][1]) / 2, (q["bbox"][2] + q["bbox"][3]) / 2,
                                  (q["bbox"][4] + q["bbox"][5]) / 2)) for q in nk["neokey"]["stemma"]],
        "note": "NeoKey holes are 2.5 mm (M2.5 tight / M2 clear). The plate sits 5.0 off "
                "the NeoKey face with 3.5 mm standoffs at these holes.",
    }
    # Screw joints. Every joint is an M2.5 screw along world X, from the outside of a
    # cheek through it (clearance + head counterbore in the cheek) into a boss on the
    # part's end face (pilot 2.2 for a self-tapping screw), which sits flush against the
    # cheek's inner face at x = +-X_IN.
    bx_l, bx_r = BOARD_CX + X_IN, BOARD_CX - X_IN      # board/keys x at world x=-X_IN/+X_IN
    jz_b = -12.35                                      # bezel mid-thickness, board frame
    jz_d = NK_FACE - 4.25                              # deck plate mid-plane, keys frame
    joints = {}
    for side, bxv in (("L", bx_l), ("R", bx_r)):
        joints["bezel_top_" + side] = tf(s0, sa, (bxv, 73.57, jz_b))
        joints["bezel_bottom_" + side] = tf(s0, sa, (bxv, 5.0, jz_b))
        joints["deck_back_" + side] = tf(k0, ka, (bxv, 29.8, jz_d))
        joints["deck_front_" + side] = tf(k0, ka, (bxv, 7.0, jz_d))
        sx = -X_IN if side == "L" else X_IN
        joints["foot_front_" + side] = [sx, -30.0, 6.0]
        joints["foot_rear_" + side] = [sx, 50.0, 6.0]
        joints["top_rear_" + side] = [sx, 62.0, 66.0]
    out["joints"] = joints
    out["joints_note"] = ("Owners: bezel_* = bezel.py, deck_* = deck.py, foot_*/top_rear_* = "
                          "braces.py; cheeks.py takes every joint. Each boss on the owning part "
                          "is a cylinder along X, od 6.0, ending flush at x=+-X_IN, pilot 2.2 "
                          "x 6 deep. The cheek gets a 2.8 clear hole and a 4.8 x 1.5 counterbore "
                          "on its outer face, with >= 3.5 mm of cheek material round each hole.")
    json.dump(out, open(os.path.join(HERE, "layout.json"), "w"), indent=1)
    for k, v in joints.items():
        print("joint", k, v)
    print("stack world bbox:", world_bbox(s0, sa, (0.05, 61.01, 0.05, 76.11, -12.63, 18.07)))
    print("neokey world bbox:", out["neokey_bbox_world"])
    print("keycaps:", out["keys_world"]["keycap_top_centres"][0])
    print("ports:", {k: v.get("mouth", v.get("centre")) for k, v in out["ports_world"].items()})


main()
