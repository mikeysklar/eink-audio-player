# SPDX-FileCopyrightText: 2026 Mikey Sklar
# SPDX-License-Identifier: MIT-0
# Handle: the round top bar across the back, which doubles as a carry handle. It pushes in
# through the left cheek's 7.4 hole until its flange stops on the left cheek, and its split
# end snaps through the right cheek's 4.0 hole. Squeeze the two prongs to take it out.
# Built in world mm along X. Print lying down on its flat, with a small support under
# the pin, which stands 1 mm off the bed.
import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import FreeCAD as App
import Part
import arcade_common as ac

L = ac.layout()
X_IN, T = L["x_in"], L["cheek_t"]
X_OUT = X_IN + T
ROD_D, FLANGE_D, FLANGE_T = 7.0, 11.0, 1.5
PIN_D, BARB_D, BARB_LEN = 3.8, 4.6, 1.4             # right cheek hole is 4.0
SLOT_W, SLOT_LEN = 1.2, 9.0                          # splits the pin into two prongs
FLAT = 0.6                                           # flat along the bottom, to print on
X_AXIS = App.Vector(1, 0, 0)
_, y, z = L["joints"]["top_rear_L"]

rod = Part.makeCylinder(ROD_D / 2, X_IN + X_OUT, App.Vector(-X_OUT, y, z), X_AXIS)
flange = Part.makeCylinder(FLANGE_D / 2, FLANGE_T, App.Vector(-X_OUT - FLANGE_T, y, z), X_AXIS)
pin = Part.makeCylinder(PIN_D / 2, T + 0.01, App.Vector(X_IN - 0.01, y, z), X_AXIS)
barb = Part.makeCone(BARB_D / 2, PIN_D / 2 - 0.3, BARB_LEN, App.Vector(X_OUT + 0.1, y, z), X_AXIS)
neck = Part.makeCylinder(PIN_D / 2, 0.11, App.Vector(X_OUT, y, z), X_AXIS)
shape = rod.fuse([flange, pin, neck, barb])
# The slot is vertical, so the prongs lie side by side on the bed and flex in Y.
shape = shape.cut(Part.makeBox(SLOT_LEN + 1, SLOT_W, 20,
                               App.Vector(X_OUT + BARB_LEN + 0.2 - SLOT_LEN, y - SLOT_W / 2, z - 10)))
# One flat on the -Z side, through the rod and the flange, to print on.
shape = shape.cut(Part.makeBox(200, 20, 10, App.Vector(-100, y - 10, z - ROD_D / 2 - 10 + FLAT)))
shape = ac.save(shape.removeSplitter(), "handle")
ac.clash(shape)
