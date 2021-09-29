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

# https://wiki.freecadweb.org/Embedding_FreeCAD
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
        from femtools.ccxtools import FemToolsCcx
        break
else:
    print("FreeCAD library was not found!")
    sys.exit(1)


class PressureVessel(object):
    """
    The base class to work with parametric pressure vessel models.
    """

    def __init__(self, filename: str, debug=True):
        self.filename = filename
        self.debug = debug

        print("Opening:", filename)
        self.doc = FreeCAD.open(filename)

        self.fea = FemToolsCcx(
            self.doc.getObject('Analysis'),
            self.doc.getObject('SolverCcxTools'))

        self.fea.update_objects()
        self.fea.setup_working_dir()
        self.fea.setup_ccx()
        err = self.fea.check_prerequisites()
        if err:
            raise ValueError("FEM error: " + err)

    def print_info(self):
        names = [obj.Name for obj in self.doc.Objects]
        print("Object names:", ", ".join(names))

        print("Sketch parameters:")
        obj = self.doc.getObject('Sketch')
        for c in obj.Constraints:
            if not c.Name:
                continue
            print("  " + c.Name, "=", c.Value, "mm")

        print("FEM parameters:")
        obj = self.doc.getObject('ConstraintPressure')
        print("  pressure =", obj.Pressure, "N")
        obj = self.doc.getObject('FEMMeshGmsh')
        print("  mesh_max =", obj.CharacteristicLengthMax)

        print("Material parameters:")
        obj = self.doc.getObject('MaterialSolid')
        print("  youngs_modulus =", obj.Material['YoungsModulus'])
        print("  poisson_ratio =", obj.Material['PoissonRatio'])
        print("  density =", obj.Material['Density'])
        print("  tensile_strength =", obj.Material['UltimateTensileStrength'])

    def set_sketch_param(self, param: str, value: float):
        obj = self.doc.getObject('Sketch')
        obj.setDatum(param, value)

    def set_pressure(self, value: float):
        obj = self.doc.getObject('ConstraintPressure')
        obj.Pressure = value

    def set_mesh_max(self, value: float):
        obj = self.doc.getObject('FEMMeshGmsh')
        obj.CharacteristicLengthMax = value

    def run_analysis(self):
        self.fea.purge_results()
        if self.doc.getObject('ccx_dat_file'):
            self.doc.removeObject('ccx_dat_file')

        self.doc.recompute()

        if self.debug:
            print("Running GMSH mesher ...", end=' ', flush=True)
        mesher = GmshTools(
            self.doc.getObject('FEMMeshGmsh'))
        err = mesher.create_mesh()
        if err:
            raise ValueError("Meshing error: " + err)
        obj = self.doc.getObject('FEMMeshGmsh').FemMesh
        if self.debug:
            print(obj.NodeCount, "nodes,",
                  obj.FaceCount, "faces,",
                  obj.VolumeCount, "volumes")

        if self.debug:
            print("Running FEM analysis ...", end=' ', flush=True)
        self.fea.update_objects()
        self.fea.write_inp_file()
        self.fea.ccx_run()
        self.fea.load_results()
        obj = self.doc.getObject('CCX_Results')
        assert obj.ResultType == 'Fem::ResultMechanical'
        if self.debug:
            print(max(obj.vonMises), "max stress")

    def get_vonmises_max(self):
        obj = self.doc.getObject('CCX_Results')
        return max(obj.vonMises)


vessel = PressureVessel('capsule.FCStd')
vessel.print_info()
vessel.run_analysis()
vessel.set_mesh_max(1.0)
vessel.print_info()
vessel.run_analysis()

if False:
    def print_objects(doc):
        print("Objects:", ", ".join([obj.Name for obj in doc.Objects]))

    def print_properties(obj):
        print(obj.Name, "properties:")
        for name in obj.PropertiesList:
            print("   ", name, "=", getattr(obj, name))

    def get_constraint(obj: Sketcher, name: str) -> Sketcher.Constraint:
        for con in obj.Constraints:
            if con.Name == name:
                return con
        raise ValueError("Constraint " + name + " not found")

    # https://wiki.freecadweb.org/FEM_Tutorial_Python
    filename = 'capsule.FCStd'
    doc = FreeCAD.open(filename)
    # print_objects(doc)

    obj = doc.getObject("Sketch")
    obj.setDatum('thickness', 2.0)
    obj.setDatum('radius', 21.0)
    obj.setDatum('length', 16.0)
    # print(obj.getDatum('thickness'))

    obj = doc.getObject('Body')
    obj.recompute(True)

    obj = doc.getObject('FEMMeshGmsh')
    # print_properties(obj)
    # print(obj.FemMesh)
    obj.CharacteristicLengthMax = 2.0
    mesh = GmshTools(obj)
    err = mesh.create_mesh()
    if err:
        print("Meshing error:", err)
    # print_properties(obj)
    print(obj.FemMesh)

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

    fea = FemToolsCcx(
        doc.getObject('Analysis'),
        doc.getObject('SolverCcxTools'))
    fea.update_objects()
    fea.setup_working_dir()
    fea.setup_ccx()
    err = fea.check_prerequisites()
    if err:
        print("FEM error:", err)

    fea.purge_results()
    fea.write_inp_file()
    fea.ccx_run()
    fea.load_results()

    # print_objects(doc)
    obj = doc.getObject('CCX_Results')
    print(obj.PropertiesList)
    print("vonMises", len(obj.vonMises), max(obj.vonMises))
    print(obj.ResultType)
    print(obj.Stats)

    fea.purge_results()
    if doc.getObject('ccx_dat_file'):
        doc.removeObject('ccx_dat_file')
    # print_objects(doc)
