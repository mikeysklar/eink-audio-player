# Mini-arcade skeleton stand: brief for part agents

Mikey wants a minimal, open SKELETON 3D-printed stand (not a closed box, "bulky fully
enclosed is yucky") that turns the landing-pad into a little desk arcade: the e-ink screen
angled up at 65 deg, and the 4 Cherry MX keys on a separate control deck in front at 10 deg,
so he can reach over and tap next song / pick artist. Mikey approved agents editing these
files without asking. Each agent writes ONLY its own part file(s) named in its task.

Folder: enclosure/ (paths below are relative to the repo root)
- layout.py -> layout.json: THE shared frame. Read layout.py's docstring and layout.json.
  World mm: desk Z=0, Z up, player at -Y looking +Y, X = player's right, symmetric about X=0.
- arcade_common.py: FreeCAD helpers (read its docstring): ac.layout(), ac.bodies() ->
  (stack, keys) placed real models, ac.stack_pt()/ac.keys_pt() board->world, ac.clash(shape),
  ac.save(shape, name). Cached models are build/stack.brep, build/keys.brep (also .step).
- Board-frame facts: enclosure/inputs/
  parts_bbox.json, measure_display.json, measure_neokey_sw1.json, measure_feather.json,
  measure_tlv.json, board.step (board frame: origin board bottom-left, Y up the board, display/battery on -Z).

Run a part script with:
    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd enclosure/parts/<name>.py
(freecadcmd runs the file under its own module name: put code at top level, no
`if __name__ == "__main__"` guard). Start each script with
    import os, sys; sys.path.insert(0, os.environ.get("EAP_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import arcade_common as ac
End it with ac.save(shape, "<name>") and ac.clash(shape).

Rules (from Mikey's CAD skill; each produced a wrong part before):
- Primitives placed by coordinate (Part.makeBox/Cylinder/Wedge, extruded polygons from
  Part.makePolygon -> Part.Face -> extrude), booleans, simple fillets on a lone primitive.
  No sketches, lofts, sweeps, named faces/edges.
- A planar part (bezel, deck) is easiest built in its body's own frame (board or keys frame,
  where it is a flat plate on Z) and then moved to world with
  `shape.transformShape(ac._matrix("stack"))` or `ac._matrix("keys")`.
- Every part: ONE valid solid (ac.save prints valid/solids), clash with stack AND keys
  = 0.000 mm3 (clearance >= 0.3 mm to real parts), min wall 1.6 mm (FDM, 0.4 nozzle),
  printable flat on one face without support where possible (say which face goes down).
- Skeleton look: thin members (bars 4-6 mm wide), generous open areas, rounded/chamfered
  ends where cheap. No solid panels except where something must be held.
- Joints: see layout.json "joints". A part between the cheeks ends ac.END_GAP (0.25) short
  of x = +-39.5, with its boss at exactly the given world point. A screwed boss takes a
  heat insert (ac.insert_hole); the other boss of the pair has an ac.STUB_D x STUB_LEN peg
  into a slot in the cheek (chassis.py). Screws: parts/fasteners.py; 12 in all.
- Ports on the player's LEFT (layout.json ports_world): USB-C, headphone jack, SW1 knob
  keep-out cylinders along -X from each mouth out past x = -50, with the given keepout_d.
  Nothing may cross them. The Feather's STEMMA QT cable runs from the stack's back to the
  NeoKey's QT connector (layout.json keys_world.neokey_qt). Leave an open path.
- Report: what you built (members, dims), print orientation, ac.save + ac.clash output
  verbatim, and anything the other parts must know.
