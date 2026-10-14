#!/usr/bin/env python3
"""Interactive assembly viewer: translucent parts and a movable section plane.

Builds the base, lid and inlay straight from enclosure.py (so it always shows the
current design, in assembled position) and adds the real board, exported from
PCB/Attendance Management System.kicad_pcb with kicad-cli, plus the battery and motor.

Needs:  pip install pyvista manifold3d numpy matplotlib     (and kicad-cli for the board)

    python view.py                      # open the viewer
    python view.py --no-board           # skip the KiCad board
    python view.py --cut y --screenshot out.png   # render one section view and exit

Keys (also printed at start):
  1-6      show / hide base, lid, inlay, board, battery, motor
  t        cycle the case: opaque -> translucent -> ghost
  c        section plane on / off (drag the arrow to tilt it, the plane to move it)
  x y z    snap the section plane to that axis, through the middle
  f        flip which side of the plane is cut away
  k        save a screenshot to view-<n>.png
  r        reset the camera        q   quit
"""
import argparse
import os
import shutil
import subprocess
import tempfile

import numpy as np
import pyvista as pv
import vtk

import enclosure as enc

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'PCB', 'Attendance Management System.kicad_pcb')
CUT_COLOUR = 'crimson'             # inside faces, seen where the plane cuts a part
CASE_MODES = (('opaque', 1.0), ('translucent', 0.35), ('ghost', 0.12))


def manifold_to_pv(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    t = np.asarray(mesh.tri_verts, dtype=np.int64)
    faces = np.hstack([np.full((len(t), 1), 3), t]).ravel()
    return pv.PolyData(v, faces).compute_normals(split_vertices=True, feature_angle=30)


def board_meshes():
    """The KiCad board as a few meshes grouped by colour, in enclosure coordinates."""
    if not shutil.which('kicad-cli') or not os.path.exists(PCB):
        print('board: kicad-cli or the .kicad_pcb not found, skipping')
        return []
    cache = os.path.join(tempfile.gettempdir(), 'ams-enclosure-pcb.glb')
    if not os.path.exists(cache) or os.path.getmtime(cache) < os.path.getmtime(PCB):
        print('board: exporting from KiCad ...')
        # user origin (100, 145) mm gives x = KiCad x - 100, y = 145 - KiCad y, as enclosure.py uses
        subprocess.run(['kicad-cli', 'pcb', 'export', 'glb', '--user-origin', '100x145mm',
                        '--include-soldermask', '--include-silkscreen', '-f', '-o', cache, PCB],
                       check=True, stdout=subprocess.DEVNULL)
    scratch = pv.Plotter(off_screen=True)
    scratch.import_gltf(cache)
    groups = {}
    for actor in scratch.renderer.actors.values():
        data = actor.GetMapper().GetInput()
        if data is None or data.GetNumberOfPoints() == 0:
            continue
        mesh = pv.wrap(data).extract_surface(algorithm='dataset_surface')
        m = actor.GetUserMatrix()
        if m is not None:
            mesh = mesh.transform(pv.array_from_vtkmatrix(m), inplace=False)
        colour = tuple(round(c, 2) for c in actor.GetProperty().GetColor())
        groups.setdefault(colour, []).append(mesh)
    scratch.close()
    # glTF is metres and y-up: (x, y, z) -> (1000 x, -1000 z, 1000 y + board underside)
    tf = np.array([[1000, 0, 0, 0], [0, 0, -1000, 0], [0, 1000, 0, enc.Z_BOARD_BOT], [0, 0, 0, 1]],
                  dtype=float)
    return [(pv.merge(ms).transform(tf, inplace=False), colour) for colour, ms in groups.items()]


def parts(with_board):
    """(name, [(mesh, colour)], is_case) for every part, in assembled position."""
    bx0, by0, bz0, bx1, by1, bz1 = enc.BATT_BOX
    battery = pv.Box((bx0, bx1, by0, by1, bz0, bz1))
    z0 = enc.MOTOR_Z[0]
    motor = pv.Cylinder(center=(*enc.MOTOR_XY, z0 + enc.MOTOR_T / 2), direction=(0, 0, 1),
                        radius=enc.MOTOR_D / 2, height=enc.MOTOR_T, resolution=48)
    out = [
        ('base', [(manifold_to_pv(enc.make_base()), '#4a6fa5')], True),
        ('lid', [(manifold_to_pv(enc.make_lid()), '#d9d9d9')], True),
        ('inlay', [(manifold_to_pv(enc.make_inlay()), '#f2a541')], True),
        ('board', board_meshes() if with_board else [], False),
        ('battery', [(battery, '#5b8c5a')], False),
        ('motor', [(motor, '#8a8a8a')], False),
    ]
    return [p for p in out if p[1]]


class Viewer:
    def __init__(self, plotter, part_list):
        self.pl = plotter
        self.parts = {}          # name -> (actors, is_case)
        self.case_mode = 0
        self.plane = vtk.vtkPlane()
        self.cut_on = False
        self.flipped = False
        self.normal, self.origin = np.array([0.0, 1.0, 0.0]), None
        for name, meshes, is_case in part_list:
            actors = []
            for mesh, colour in meshes:
                a = plotter.add_mesh(mesh, color=colour, smooth_shading=True, specular=0.2)
                actors.append(a)
            self.parts[name] = (actors, is_case)
        b = np.array(plotter.bounds)
        self.centre = (b[::2] + b[1::2]) / 2
        self.origin = self.centre.copy()

    # ---------------------------------------------------------- translucency
    def set_case_mode(self, mode):
        self.case_mode = mode % len(CASE_MODES)
        opacity = CASE_MODES[self.case_mode][1]
        for actors, is_case in self.parts.values():
            if is_case:
                for a in actors:
                    a.prop.opacity = opacity
        self.refresh_backfaces()
        self.status()

    def toggle(self, name):
        if name in self.parts:
            for a in self.parts[name][0]:
                a.SetVisibility(not a.GetVisibility())
            self.status()

    # ---------------------------------------------------------- section plane
    def all_actors(self):
        return [a for actors, _ in self.parts.values() for a in actors]

    def apply_plane(self):
        n = -self.normal if self.flipped else self.normal
        self.plane.SetNormal(*n)
        self.plane.SetOrigin(*self.origin)
        self.pl.render()

    def on_widget(self, normal, origin):
        self.normal, self.origin = np.array(normal), np.array(origin)
        self.apply_plane()

    def set_cut(self, on):
        self.cut_on = on
        self.pl.clear_plane_widgets()
        for a in self.all_actors():
            mapper = a.GetMapper()
            mapper.RemoveAllClippingPlanes()
            if on:
                mapper.AddClippingPlane(self.plane)
        self.refresh_backfaces()
        if on:
            self.pl.add_plane_widget(self.on_widget, normal=self.normal, origin=self.origin,
                                     bounds=self.pl.bounds, factor=1.15, outline_translation=False,
                                     normal_rotation=True, implicit=True, color='white',
                                     interaction_event='always')
            self.apply_plane()
        self.status()

    def refresh_backfaces(self):
        """A cut opaque part shows its inside faces: colour them so the section reads as solid.

        Translucent parts keep their own colour inside, or every wall behind them would turn red."""
        for a in self.all_actors():
            if self.cut_on and a.prop.opacity >= 1.0:
                a.backface_prop = pv.Property(color=CUT_COLOUR, ambient=0.3, diffuse=0.7)
            else:
                a.SetBackfaceProperty(None)

    def snap(self, axis):
        self.normal = np.eye(3)[axis]
        self.origin = self.centre.copy()
        self.set_cut(True)

    def flip(self):
        self.flipped = not self.flipped
        if self.cut_on:
            self.apply_plane()
        self.status()

    # ---------------------------------------------------------- odds and ends
    def screenshot(self):
        n = 1
        while os.path.exists(f'view-{n}.png'):
            n += 1
        self.pl.screenshot(f'view-{n}.png')
        print(f'saved view-{n}.png')

    def status(self):
        shown = [n for n, (actors, _) in self.parts.items() if actors[0].GetVisibility()]
        cut = 'off'
        if self.cut_on:
            cut = 'normal ' + ', '.join(f'{c:+.2f}' for c in self.normal) + (' (flipped)' if self.flipped else '')
        self.pl.add_text(f'case: {CASE_MODES[self.case_mode][0]}   section: {cut}\n'
                         f'shown: {" ".join(shown)}', position='upper_left', font_size=9,
                         name='status')

    def bind_keys(self):
        for i, name in enumerate(self.parts):
            self.pl.add_key_event(str(i + 1), lambda n=name: self.toggle(n))
        self.pl.add_key_event('t', lambda: self.set_case_mode(self.case_mode + 1))
        self.pl.add_key_event('c', lambda: self.set_cut(not self.cut_on))
        for i, k in enumerate('xyz'):
            self.pl.add_key_event(k, lambda i=i: self.snap(i))
        self.pl.add_key_event('f', self.flip)
        self.pl.add_key_event('k', self.screenshot)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--no-board', action='store_true', help='skip the KiCad board model')
    ap.add_argument('--case', choices=[m for m, _ in CASE_MODES], default='translucent')
    ap.add_argument('--cut', choices='xyz', help='start with a section plane on this axis')
    ap.add_argument('--screenshot', metavar='PNG', help='render once to this file and exit')
    args = ap.parse_args()

    pl = pv.Plotter(off_screen=bool(args.screenshot), window_size=(1400, 900),
                    title='Enclosure assembly')
    pl.set_background('#2b2b2b', top='#4a4a4a')
    pl.enable_depth_peeling(number_of_peels=8)     # correct ordering of translucent parts
    pl.enable_anti_aliasing('ssaa')
    v = Viewer(pl, parts(not args.no_board))
    v.set_case_mode([m for m, _ in CASE_MODES].index(args.case))
    if args.cut:
        v.snap('xyz'.index(args.cut))
    pl.add_axes()
    pl.camera_position = 'iso'
    pl.camera.azimuth = 200
    pl.camera.elevation = 15
    pl.reset_camera()

    if args.screenshot:
        pl.screenshot(args.screenshot)
        print(f'saved {args.screenshot}')
        return
    v.bind_keys()
    print(__doc__[__doc__.index('Keys'):])
    pl.show()


if __name__ == '__main__':
    main()
