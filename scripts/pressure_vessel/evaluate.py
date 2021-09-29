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
        from FreeCAD import Units
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
        """
        Creates a pressure vessel analysis class that can be used to run
        multiple simulations for the given design template by changing its
        parameters.
        """
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
        """
        Prints out all relevant information from the design template
        and the output of design analysis.
        """
        names = [obj.Name for obj in self.doc.Objects]
        print("Object names:", ", ".join(names))

        obj = self.doc.getObject('Sketch')
        print("Sketch parameters:")
        for c in obj.Constraints:
            if not c.Name:
                continue
            print("  " + c.Name, "=", c.Value, "mm")

        obj = self.doc.getObject('ConstraintPressure')
        print("FEM parameters:")
        print("  pressure =", obj.Pressure, "MPa")
        obj = self.doc.getObject('FEMMeshGmsh')
        print("  mesh_length =", obj.CharacteristicLengthMax)

        obj = self.doc.getObject('MaterialSolid')
        print("Material parameters:")
        print("  youngs_modulus =", obj.Material['YoungsModulus'])
        print("  poisson_ratio =", obj.Material['PoissonRatio'])
        print("  tensile_strength =", obj.Material['UltimateTensileStrength'])
        print("  density =", obj.Material['Density'])

        obj = self.doc.getObject('CCX_Results')
        if obj:
            print("FEM results:")
            print("  vonmises_stress = {:.2f} MPa".format(max(obj.vonMises)))
            print("  tresca_stress = {:.2f} MPa".format(max(obj.MaxShear)))
            print("  displacement = {:.2f} mm".format(
                max(obj.DisplacementLengths)))
#            print("  pass_status =", "true" if self.get_pass_status() else "false")
        else:
            print("FEM Results: None")

    @staticmethod
    def print_properties(obj):
        print(obj.Name, "properties:")
        for name in obj.PropertiesList:
            print(" ", name, "=", getattr(obj, name))

    def set_sketch_length(self, param: str, value: float):
        """
        Sets a length constraint of the sketch object in millimeters.
        """
        obj = self.doc.getObject('Sketch')
        obj.setDatum(param, Units.Quantity(value, Units.Unit('mm')))

    def get_sketch_length(self, param: str) -> float:
        obj = self.doc.getObject('Sketch')
        return obj.getDatum(param).getValueAs('mm')

    def set_pressure(self, value: float):
        """
        Sets the outside pressure acting on the vessel in mega pascals.
        """
        obj = self.doc.getObject('ConstraintPressure')
        obj.Pressure = float(value)

    def get_pressure(self) -> float:
        obj = self.doc.getObject('ConstraintPressure')
        return float(obj.Pressure)

    def set_mesh_length(self, value: float):
        """
        Sets the maximum edge length for the meshing algorithm in millimeters.
        """
        obj = self.doc.getObject('FEMMeshGmsh')
        obj.CharacteristicLengthMax = Units.Quantity(value, Units.Unit('mm'))

    def get_mesh_length(self) -> float:
        obj = self.doc.getObject('FEMMeshGmsh')
        return obj.CharacteristicLengthMax.getValueAs('mm')

    def set_youngs_modulus(self, value: float):
        """
        Sets the Youngs modulus of the material in mega pascals.
        """
        obj = self.doc.getObject('MaterialSolid')
        mat = dict(obj.Material)
        mat['YoungsModulus'] = str(value) + ' MPa'
        obj.Material = mat

    def get_youngs_modulus(self) -> float:
        obj = self.doc.getObject('MaterialSolid')
        return Units.Quantity(obj.Material['YoungsModulus']).getValueAs('MPa')

    def set_poisson_ratio(self, value: float):
        """
        Sets the poisson ratio of the material.
        """
        obj = self.doc.getObject('MaterialSolid')
        mat = dict(obj.Material)
        mat['PoissonRatio'] = str(value)
        obj.Material = mat

    def get_poisson_ratio(self):
        obj = self.doc.getObject('MaterialSolid')
        return float(obj.Material['PoissonRatio'])

    def set_tensile_strength(self, value: float):
        """
        Sets the ultimate tensile strength of the material in mega pascals.
        """
        obj = self.doc.getObject('MaterialSolid')
        mat = dict(obj.Material)
        mat['UltimateTensileStrength'] = str(value) + ' MPa'
        obj.Material = mat

    def get_tensile_strength(self) -> float:
        obj = self.doc.getObject('MaterialSolid')
        return Units.Quantity(obj.Material['UltimateTensileStrength']).getValueAs('MPa')

    def set_density(self, value: float):
        obj = self.doc.getObject('MaterialSolid')
        obj.Material['Density'] = value

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
            print("vonMises stress: {:.2f} MPa".format(max(obj.vonMises)))

    def get_vonmises_stress(self) -> float:
        obj = self.doc.getObject('CCX_Results')
        return max(obj.vonMises)

    def get_tresca_stress(self) -> float:
        obj = self.doc.getObject('CCX_Results')
        return max(obj.MaxShear)

    def get_displacement(self) -> float:
        obj = self.doc.getObject('CCX_Results')
        return max(obj.DisplacementLengths)

    def get_pass_status(self) -> bool:
        obj = self.doc.getObject('MaterialSolid')
        return self.get_vonmises_stress() <= obj.Material['UltimateTensileStrength']


vessel = PressureVessel('capsule.FCStd')
# vessel.run_analysis()
vessel.set_sketch_length('radius', 1.1)
assert vessel.get_sketch_length('radius') == 1.1
vessel.set_pressure(2.2)
assert vessel.get_pressure() == 2.2
vessel.set_mesh_length(3.3)
assert vessel.get_mesh_length() == 3.3
vessel.set_youngs_modulus(4.4)
assert vessel.get_youngs_modulus() == 4.4
vessel.set_poisson_ratio(5.5)
assert vessel.get_poisson_ratio() == 5.5
vessel.set_tensile_strength(6.6)
assert vessel.get_tensile_strength() == 6.6
vessel.print_info()
