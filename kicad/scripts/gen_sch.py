#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT
# Writes its output next to itself (scripts/). Used to generate the schematic from subnets.json; copy the output into kicad/ to use it.
"""
Write eink-audio-player.kicad_sch from subnets.json (written by build_pcb.py)
and netlist.py.

Plain python3 is enough (no pcbnew). Symbols are copied verbatim from the
stock KiCad libraries into lib_symbols. Nets come from local labels on short
wire stubs, so they come out as /NAME, which is what build_pcb.py expects.
Pads listed in netlist.OPEN get a no-connect flag. Each 0R splits its net
in two, so subnets.json, not netlist.NETS, names the nets (EN, EN_R4_R5...).

Symbol UUIDs are fixed (uuid5 of the reference) so re-running this does not
break the footprint links build_pcb.py makes with SetPath().

  J1  Feather RP2350 JP1 socket (16)     J2  Feather RP2350 JP3 socket (12)
  J9  TLV320DAC3100 JP3 socket (10)      J10 TLV320DAC3100 JP1 socket (8)
  J4  EYESPI 1-9 (5613 breakout JP2)  J5  EYESPI 10-18 (5613 breakout JP1)
  SW1 MSK-12C03 power slide switch
  R1-R4  0R 0805 jumpers (single-sided board; R4 joins two pieces of the GND fill)
  H1-H7  M2.5 mounting holes
"""

import json
import os
import uuid

import netlist
import plan

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "eink-audio-player.kicad_sch")
SYM_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
NS = uuid.UUID("5e1c0a77-2b5d-4c1e-9a0b-6c7d8e9f0a10")
ROOT_UUID = str(uuid.uuid5(NS, "root"))


def uid(ref):
    return str(uuid.uuid5(NS, ref))


def u():
    return str(uuid.uuid4())


def lib_block(lib, name):
    s = open(os.path.join(SYM_DIR, lib + ".kicad_sym")).read()
    i = s.index(f'(symbol "{name}"')
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                blk = s[i:j + 1]
                return blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    raise ValueError(name)


def prop(name, value, x, y, hide=False):
    h = " (hide yes)" if hide else ""
    return (f'\t\t(property "{name}" "{value}" (at {x} {y} 0)\n'
            f'\t\t\t(effects (font (size 1.27 1.27)){h})\n\t\t)\n')


def symbol(lib_id, ref, value, fp, x, y, pins, ref_dy=-27.94, val_dy=27.94):
    bom = "no" if lib_id == "Mechanical:MountingHole" else "yes"
    out = (f'\t(symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)\n'
           f'\t\t(exclude_from_sim no) (in_bom {bom}) (on_board yes) (dnp no)\n'
           f'\t\t(uuid "{uid(ref)}")\n')
    out += prop("Reference", ref, x + 2.54, y + ref_dy)
    out += prop("Value", value, x + 2.54, y + val_dy)
    out += prop("Footprint", fp, x, y, hide=True)
    out += prop("Datasheet", "~", x, y, hide=True)
    for p in pins:
        out += f'\t\t(pin "{p}" (uuid "{u()}"))\n'
    out += (f'\t\t(instances (project "eink-audio-player"\n'
            f'\t\t\t(path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))\n\t)\n')
    return out


def wire(x1, y1, x2, y2):
    return (f'\t(wire (pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'\t\t(stroke (width 0) (type default)) (uuid "{u()}"))\n')


def label(name, x, y, rot=0):
    just = "right bottom" if rot == 180 else "left bottom"
    return (f'\t(label "{name}" (at {x} {y} {rot}) (fields_autoplaced yes)\n'
            f'\t\t(effects (font (size 1.27 1.27)) (justify {just}))\n'
            f'\t\t(uuid "{u()}"))\n')


def no_connect(x, y):
    return f'\t(no_connect (at {x} {y}) (uuid "{u()}"))\n'


def text(t, x, y):
    return (f'\t(text "{t}" (exclude_from_sim no) (at {x} {y} 0)\n'
            f'\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'\t\t(uuid "{u()}"))\n')


def r(v):
    return round(v, 2)


def main():
    sub = json.load(open(os.path.join(SCRIPT_DIR, "subnets.json")))
    pn = {tuple(k.split(".")): v for k, v in sub.items()}
    for (ref, num), net in netlist.pad_net().items():
        if not pn.get((ref, num), "").startswith(net):
            raise SystemExit(f"{ref}.{num}: subnets.json has {pn.get((ref, num))}, not {net}")
    body = ""

    def pin_stub(ref, num, px, py, side):
        """Label or no-connect on the pin at (px, py); side -1 = pin points west."""
        nonlocal body
        net = pn.get((ref, str(num)))
        if net:
            x2 = px + side * 5.08
            body += wire(r(px), r(py), r(x2), r(py))
            body += label(net, r(x2), r(py), 180 if side < 0 else 0)
        else:
            if (ref, str(num)) not in netlist.OPEN:
                raise SystemExit(f"{ref}.{num} is neither on a net nor in OPEN")
            body += no_connect(r(px), r(py))

    def conn(lib, name, ref, value, fp, x, y, count, mp=False):
        nonlocal body
        pins = [str(n) for n in range(1, count + 1)] + (["MP"] if mp else [])
        body += symbol(f"{lib}:{name}", ref, value, fp, x, y, pins,
                       ref_dy=-(2.54 * count / 2 + 5.08), val_dy=2.54 * count / 2 + 7.62)
        top = 2.54 * ((count - 1) // 2)   # pin 1 (the stock symbols put it here)
        for n in range(1, count + 1):
            pin_stub(ref, n, x - 5.08, y - (top - 2.54 * (n - 1)), -1)
        if mp:
            px, py = x, y + 27.94
            if ("J4", "MP") in pn:
                raise SystemExit("J4 MP on a net: not drawn")
            body += no_connect(r(px), r(py))

    S = "Connector_PinSocket_2.54mm:PinSocket_1x{:02d}_P2.54mm_Vertical_SMD_Pin1Left"
    conn("Connector", "Conn_01x16_Socket", "J1", "Feather 16-pin", S.format(16),
         60.96, 76.2, 16)
    conn("Connector", "Conn_01x12_Socket", "J2", "Feather 12-pin", S.format(12),
         60.96, 139.7, 12)
    conn("Connector", "Conn_01x10_Socket", "J9", "TLV VIN..SPKP", S.format(10),
         132.08, 76.2, 10)
    conn("Connector", "Conn_01x08_Socket", "J10", "TLV MICBIAS..MIC", S.format(8),
         132.08, 134.62, 8)
    conn("Connector", "Conn_01x09_Socket", "J4", "EYESPI 1-9 (5613 JP2)", S.format(9),
         203.2, 76.2, 9)
    conn("Connector", "Conn_01x09_Socket", "J5", "EYESPI 10-18 (5613 JP1)", S.format(9),
         203.2, 106.68, 9)

    # SW1: SW_SPDT, A (1) at (+5.08, -2.54), B (2) at (-5.08, 0), C (3) at (+5.08, +2.54)
    sx, sy = 203.2, 139.7
    body += symbol("Switch:SW_SPDT", "SW1", "Power (MSK-12C03)", "eink-audio-player:SW_SPDT_MSK-12C03",
                   sx, sy, ["1", "2", "3"], ref_dy=-7.62, val_dy=7.62)
    pin_stub("SW1", 1, sx + 5.08, sy - 2.54, +1)
    pin_stub("SW1", 2, sx - 5.08, sy, -1)
    pin_stub("SW1", 3, sx + 5.08, sy + 2.54, +1)

    # 0R jumpers: Device:R pin 1 at the top (schematic y - 3.81), pin 2 below.
    jx = 241.3
    for k, ref in enumerate(plan.JUMPERS):
        x, y = jx + 15.24 * (k % 4), 76.2 + 22.86 * (k // 4)
        body += symbol("Device:R", ref, "0R", "Resistor_SMD:R_0805_2012Metric",
                       x, y, ["1", "2"], ref_dy=-1.27, val_dy=1.27)
        for num, py in (("1", y - 3.81), ("2", y + 3.81)):
            end = r(py - 2.54 if num == "1" else py + 2.54)
            body += wire(x, r(py), x, end)
            body += label(pn[(ref, num)], x, end, 0)
    # H1-H7 M2.5 board holes
    for k in range(7):
        ref = f"H{k + 1}"
        body += symbol("Mechanical:MountingHole", ref, "M2.5", "MountingHole:MountingHole_2.7mm",
                       241.3 + 15.24 * k, 134.62, [], ref_dy=-3.81, val_dy=3.81)

    body += text("Single-sided F.Cu, no vias, GND fill. R1-R4 are 0R jumpers over crossing traces.",
                 30.48, 177.8)
    body += text("I2S on A0 BCLK, A1 WSEL, A2 DIN (i2s-amp-shim pins). EYESPI on board.SPI.",
                 30.48, 182.88)
    body += text("TLV RST (J10.5) open: 10K pull-up on the breakout. MCLK open: PLL from BCLK.",
                 30.48, 187.96)

    libs = "".join("\t\t" + lib_block(lib, n).replace("\n", "\n\t\t") + "\n"
                   for lib, n in [("Connector", "Conn_01x16_Socket"),
                                  ("Connector", "Conn_01x12_Socket"),
                                  ("Connector", "Conn_01x10_Socket"),
                                  ("Connector", "Conn_01x08_Socket"),
                                  ("Connector", "Conn_01x09_Socket"),
                                  ("Switch", "SW_SPDT"),
                                  ("Device", "R"),
                                  ("Mechanical", "MountingHole")])

    sch = (f'(kicad_sch\n\t(version 20231120)\n\t(generator "eeschema")\n'
           f'\t(generator_version "8.0")\n\t(uuid "{ROOT_UUID}")\n\t(paper "A3")\n'
           f'\t(title_block (title "eink-audio-player") (company "mikeysklar"))\n'
           f'\t(lib_symbols\n{libs}\t)\n'
           f'{body}'
           f'\t(sheet_instances (path "/" (page "1")))\n)\n')
    with open(OUT, "w") as f:
        f.write(sch)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
