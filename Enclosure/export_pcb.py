#!/usr/bin/env python3
"""Export the populated board as pcb.step and stl/pcb.stl, in the same x/y frame as enclosure.py.

The KiCad library has no 3D models for three of the board's parts. This script
exports from a temporary copy of the board with the models swapped:
  J2  JST-XA footprint     -> models/JST_XH_B2B-XH-A_C158012.step   (JLCPCB/EasyEDA, LCSC C158012):
                              the XH header actually fitted, same 2.5 mm pitch and holes
  Y1  EuroQuartz EQ161     -> models/Crystal_3215_C95361.step         (JLCPCB/EasyEDA, LCSC C95361)
  J1  GCT USB4110          -> KiCad's GCT USB4105 16P top-mount, a stand-in
                              (JLCPCB has no model for C5143397)
Left out, as they are not fitted: the four Wuerth reverse-mount standoffs (not in the
BOM; the enclosure's bosses take their place), J3 (PN532 socket) and the J4 header
(the motor leads are soldered straight into its holes). PCB/*.kicad_pcb is not modified.

Origin: x = KiCad x - 100, y = 145 - KiCad y, matching enclosure.py. The board's
underside is at z = 0; in the enclosure it sits at z = Z_BOARD_BOT (3.8).

Needs kicad-cli (KiCad 10). The ST25R3916 model comes from KICAD_3RD_PARTY, set below.
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.environ.get('AMS_PCB', os.path.join(HERE, '..', 'PCB', 'Attendance Management System.kicad_pcb'))
THIRD_PARTY = '/home/rajinthan/Documents/kicad/external_libs'
LIB = '${KICAD10_3DMODEL_DIR}/'
MODELS = os.path.join(HERE, 'models')

# (model path in the board file, replacement path, offset "x y z" in mm)
SWAPS = [
    (LIB + 'Connector_JST.3dshapes/JST_XA_B02B-XASK-1_1x02_P2.50mm_Vertical.step',
     os.path.join(MODELS, 'JST_XH_B2B-XH-A_C158012.step'), '1.25 0 0'),      # model is centred between the pins
    (LIB + 'Crystal.3dshapes/Crystal_SMD_EuroQuartz_EQ161-2Pin_3.2x1.5mm.step',
     os.path.join(MODELS, 'Crystal_3215_C95361.step'), None),
    (LIB + 'Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4110.step',
     LIB + 'Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step', None),
]
DROP = [LIB + 'Mounting_Wuerth.3dshapes/Mounting_Wuerth_WA-SMSR-3.2mm_H10.6mm_ReverseMount_9775106960',
        LIB + 'Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x08_P2.54mm_Vertical',      # J3
        LIB + 'Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical']      # J4


def model_block(s, start):
    """End index of the (model ...) block starting at start."""
    depth = 0
    for i in range(start, len(s)):
        depth += {'(': 1, ')': -1}.get(s[i], 0)
        if depth == 0:
            return i + 1
    raise ValueError('unbalanced model block')


def main():
    s = open(PCB).read()
    for old, new, offset in SWAPS:
        head = f'(model "{old}"'
        i = s.index(head)
        j = model_block(s, i)
        block = s[i:j].replace(head, f'(model "{new}"')
        if offset:
            block = block.replace('(offset\n\t\t\t\t(xyz 0 0 0)', f'(offset\n\t\t\t\t(xyz {offset})', 1)
        s = s[:i] + block + s[j:]
    for drop in DROP:
        while (i := s.find(f'(model "{drop}')) >= 0:
            s = s[:i] + s[model_block(s, i):]

    with tempfile.TemporaryDirectory() as tmp:
        board = os.path.join(tmp, 'board.kicad_pcb')
        with open(board, 'w') as f:
            f.write(s)
        common = ['--user-origin', '100x145mm', '-D', f'KICAD_3RD_PARTY={THIRD_PARTY}', '-f']
        out = os.path.join(HERE, 'stl')
        subprocess.run(['kicad-cli', 'pcb', 'export', 'step', '--include-silkscreen',
                        '--include-soldermask', *common,
                        '-o', os.path.join(HERE, 'pcb.step'), board], check=True)
        # STL: solids only (silkscreen and mask would be zero-thickness faces)
        subprocess.run(['kicad-cli', 'pcb', 'export', 'stl', *common,
                        '-o', os.path.join(out, 'pcb.stl'), board], check=True)


if __name__ == '__main__':
    main()
