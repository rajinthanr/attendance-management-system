# Enclosure

A slim two-part printed case for the logger board. It assumes the board's tall parts are
on the **back**: J2 (battery connector), J5 (SWD header) and TH1 (NTC). J4 takes the
motor leads soldered straight into its holes, and J3 (PN532 socket) is not fitted.

- **Lid:** a thin shell with a flat top, hollow over the board. Inside, the only
  structures are walled light pipes down to each LED, guide tubes down to BOOT0 and
  RESET, a skirt round the power button and the four screw columns. The power button is
  a flap cut into the top, exactly flush with it. The tap area is marked over the NFC
  loop, 5.2 mm above the antenna.
- **USB-C:** a three-sided bezel: a U-notch in the front edge, open through the top and
  chamfered on the left, right and bottom, takes the cable's overmould (any height). A
  thin inner face behind it hugs the socket, so only the socket shows and the plug still
  seats within 0.5 mm.
- **Base:** the deep part. The battery and the motor are clamped between raised seats
  and the underside of the board, so they can't move. The screw bosses are ribbed to the
  nearby walls or gusseted, and the five board-support posts are gusseted at the floor.

Outside size: **65.2 × 93.7 × 18.8 mm**: 1.4 mm floor, 10.6 mm under the board, the
1.6 mm board and a 5.2 mm lid. Under the board, the battery plug sets the depth: the
JST-XH header in J2 is 9.8 mm with its plug fitted (JST datasheet), plus 1.6 mm (with a
0.8 mm floor pocket) for the leads to bend flat. The lid only has to clear the 3.3 mm
USB-C socket, since the port is open through the top.

`enclosure.py` is parametric (every size is a named constant at the top) and writes the
STLs to `stl/`:

```sh
pip install manifold3d numpy matplotlib
python enclosure.py      # prints the size and screws, exits non-zero if anything would collide
```

It reads every part (side, courtyard, through-hole pads) from
`PCB/Attendance Management System.kicad_pcb` at run time; set `AMS_PCB` to point it at
another board file. It then runs a fit check: the board, every part on both sides, the
leads, the battery and the motor against the case, and the battery and motor against the
parts. It also picks a standard screw length for each hole. `view.py` shows the assembly
interactively, with a section plane.

| File in `stl/` | What it is |
|---|---|
| `base.stl`, `lid.stl`, `lid_inlay.stl` | the printed parts, each in its print orientation |
| `battery.stl`, `motor.stl` | reference models of the 803040 cell and the coin motor (with short lead stubs), in their fitted position; not for printing |
| `pcb.stl` | the populated board, written by `export_pcb.py` (see below) |
| `assembly.stl` | everything in its fitted position: base, lid, inlay, board, battery and motor |

`assembly.stl` takes the board from `stl/pcb.stl`, so run `export_pcb.py` first after a
board change, then `enclosure.py`.

## Designed for moulding

Both parts would also suit injection moulding. Printing doesn't need any of this, and it
costs nothing there.

- **One straight pull per part**, with the parting line at the seam. There are no
  undercuts: every face is reachable from its side of the tool, checked face by face
  with exact rays. The USB-C port is split by the seam, so each half is an open notch.
- **Draft:** 1° on the walls, the lip and the rebate; 0.5° on the bosses, posts, ribs,
  light pipes, guide tubes, columns, holes and slots, each tapering away from its side of
  the tool. 99.8 % of the base's side faces and 92 % of the lid's are drafted. What's left
  is the debossed marks (0.6 mm deep; engraving gets its draft in the tool) and the faces
  of the USB step.
- **Even walls:** thick sections are cored out. The battery sits on a rib grid, the posts
  and the motor pedestal are tubes, and ribs and gussets are 1.2 mm (about 0.55 × the
  2.2 mm wall).

The draft angles are `DRAFT_WALL` and `DRAFT_CORE` at the top of `enclosure.py`.

## Board 3D model

The populated board comes in two formats: `pcb.step` for CAD (Fusion 360, FreeCAD,
Onshape) and `stl/pcb.stl` for mesh viewers and slicers (no silkscreen). Both share
`enclosure.py`'s x/y (the board's lower-left corner is at the origin). The board's
underside is at z = 0, so raise it **12.0 mm** to seat it in the base.

Regenerate both after a board change with `python export_pcb.py` (needs `kicad-cli`;
`AMS_PCB` works here too). The script exports from a temporary copy of the board, so the
`.kicad_pcb` is never edited. It swaps in models KiCad doesn't have and leaves out parts
that aren't fitted:

| Part | In the model |
|---|---|
| J2 (JST-XA footprint) | the JST-XH B2B-XH-A actually fitted: JLCPCB/EasyEDA model, LCSC C158012 (`models/`) |
| Y1 32.768 kHz crystal | JLCPCB/EasyEDA model, LCSC C95361 (`models/`) |
| J1 GCT USB4110 | KiCad's GCT USB4105 as a stand-in (JLCPCB has no model for C5143397) |
| J3 PN532 socket, J4 header | left out: not fitted |
| Würth reverse-mount standoffs | left out: not in the BOM; the enclosure's bosses take their place |

## Printing

Neither part needs supports. PLA or PETG, 0.2 mm layers, 3 perimeters, 20 % infill.
PETG is better for the button flap, which flexes every press.

| File | Orientation | Notes |
|---|---|---|
| `base.stl` | floor on the bed | The nut pockets are bridged over; that's normal |
| `lid.stl` | top face on the bed | The marks print into the first layers; the light pipes, guide tubes and button stem grow up from the top |
| `lid_inlay.stl` | same position as the lid | Optional: the tap graphic and power-button marks in a second colour |

**Making the tap area stand out** (pick one):
- **Single-colour printer:** add a filament change at **0.6 mm** print height (after
  the 3rd layer at 0.2 mm). The first 0.6 mm is the top face: print it in a light
  colour and the rest in a dark one, and the tap graphic and the power-button marks show
  dark on light.
- **Multi-material printer:** load `lid.stl` and `lid_inlay.stl` as two parts of one
  object, and give the inlay the contrasting filament.
- **No colour change:** fill the debossed graphic with paint or a paint marker.

## Parts

- 4× M3×16 countersunk screw (ISO 10642 / DIN 7991)
- 4× M3 hex nut
- 803040 LiPo, 1000 mAh (40 × 30 × 8 mm), with a JST-XH plug for J2; thin, flexible
  (silicone) leads, since they bend flat in 1.6 mm under the plug
- 10 mm coin vibration motor
- Foam pads: 1 mm thick (battery) and 0.5 mm thick (motor), e.g. double-sided foam tape

## Assembly

1. **Battery:** put a 1 mm foam pad on top of it and lay it in the walled bay. The leads
   go to the open (right-hand) end, towards J2.
2. **Motor:** put a 0.5 mm pad on top of it and drop it into the cup on the pedestal,
   leads out through the slot towards J4. Solder the leads into the J4 holes.
3. **Board:** plug the battery into J2 (on the back of the board), then lay the board
   in the base on the four bosses and five posts. USB-C goes to the front opening.
   The board lands on the battery and motor pads.
4. **Lid:** check the button stem lines up with SW3 (front-left), then lay the lid over
   the board, onto the base lip.
5. **Screws:** push an M3 nut into each hex pocket under the base, then drive the four
   M3×16 screws down through the lid. As the screws tighten,
   the board presses the battery and motor onto their seats, which holds them in place.
   Tighten until the lid seats, and no further.

## On the device

- **Tap area:** the outlined area with the waves, over the NFC loop.
- **Power button:** the flap at the front-left corner. Press the ringed power symbol: it
  sits right over the switch. It's flush with the top, and about 2–3 N clicks it, most
  of that the switch itself. If it ever feels pre-pressed (the stem printed long), raise
  `STEM_CLR`.
- **BOOT0 / RESET:** the two pin holes beside the panel. BOOT0 is the nearer one; press
  them with a paper clip. Firmware updates can go over USB DFU with BOOT0 held at reset.
- **LEDs:** the pair of holes behind the BOOT0 hole are the status LEDs (green, red). The
  three holes by the USB-C opening are the charger LEDs, lit only while USB is plugged in.
- **SWD:** J5 is on the back of the board, inside the case, so open the case to debug.

## Caveats

- **Battery and motor sizes:** these listings give no tolerances. The foam pads take up
  about ±0.3 mm; beyond that, adjust `BATT_*`, `BATT_PAD`, `MOTOR_*` or `MOTOR_PAD`.
- **Read range:** the top is 5.2 mm above the loop (3.6 mm air plus the 1.6 mm top), and
  the battery is 15 mm in front of it. Check read range and tuning with the case closed.
- **BOM:** the board's footprint and BOM still name the JST-XA (B02B-XASK-1, C263753).
  The XH header fits the same holes; order the XH (B2B-XH-A, C158012) instead.
- **Lower case:** soldering the battery leads straight into J2's holes would let `BELOW`
  drop to 9.0 mm (the battery with its pad, and the J5 header, then set it), about 17.2 mm
  overall. The fit check reports anything else that changes, including the screw lengths.
