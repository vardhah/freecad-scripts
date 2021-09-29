#!/usr/bin/env python3
# Copyright (C) 2021, Miklos Maroti
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys


def import_freecad():
    # https://wiki.freecadweb.org/Embedding_FreeCAD
    global FreeCAD, Part, Sketcher, GmshTools
    freecad_libs = [
        '/usr/local/lib/FreeCAD.so',
    ]
    for lib in freecad_libs:
        if os.path.exists(lib):
            path = os.path.dirname(lib)
            if path not in sys.path:
                sys.path.append(path)
            import FreeCAD
            import Part
            import Sketcher
            from femmesh.gmshtools import GmshTools
            return
    else:
        print("FreeCAD library was not found!")
        sys.exit(1)


import_freecad()
#help(FreeCAD)

def print_properties(obj):
    print(obj.Name, "properties:")
    for name in obj.PropertiesList:
        print(name, "=", getattr(obj, name))

def get_constraint(obj: Sketcher, name: str) -> Sketcher.Constraint:
    for con in obj.Constraints:
        if con.Name == name:
            return con
    raise ValueError("Constraint " + name + " not found")


filename = 'capsule.FCStd'
doc = FreeCAD.open(filename)
# for obj in doc.Objects:
#     print(obj.Name)

obj = doc.getObject("Sketch")
obj.setDatum('thickness', 2.0)
obj.setDatum('radius', 21.0)
obj.setDatum('length', 16.0)
# print(obj.getDatum('thickness'))

obj = doc.getObject('Body')
obj.recompute(True)

obj = doc.getObject('FEMMeshGmsh')
# print_properties(obj)
obj.CharacteristicLengthMax = 5.0
mesh = GmshTools(obj)
err = mesh.create_mesh()
if err:
    print("Meshing error:", err)
# print_properties(obj)

obj = doc.getObject('ConstraintPressure')
obj.Pressure = 123.0

obj = doc.getObject('MaterialSolid')
# print(obj.Material)
obj.Material = {
    'Name': "Steel-Generic",
    'YoungsModulus': "210000 MPa",
    'PoissonRatio': "0.30",
    'Density': "7900 kg/m^3",
}
