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

from freecad_scripts.libs import FreeCAD, Units, GmshTools, FemToolsCcx


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

        if self.doc.getObject('FEMMeshGmsh').FemMesh.NodeCount:
            print("WARNING: clean the mesh in the model to save space")

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

        obj = self.doc.getObject('FEMMeshGmsh').FemMesh
        if obj:
            print("Mesh properties:")
            print("  nodes =", obj.NodeCount)
            print("  edges =", obj.EdgeCount)
            print("  faces =", obj.FaceCount)
            print("  volumes =", obj.VolumeCount)
        else:
            print("Mesh properties: none")

        obj = self.doc.getObject('CCX_Results')
        if obj:
            print("FEM results:")
            print("  vonmises_stress = {:.2f} MPa".format(max(obj.vonMises)))
            print("  tresca_stress = {:.2f} MPa".format(max(obj.MaxShear)))
            print("  displacement = {:.2f} mm".format(
                max(obj.DisplacementLengths)))
            print("  has_failed =", "true" if self.has_failed() else "false")
        else:
            print("FEM Results: none")

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
        """
        Sets the density of the material in kg/m3.
        """
        obj = self.doc.getObject('MaterialSolid')
        mat = dict(obj.Material)
        mat['Density'] = str(value) + ' kg/m^3'
        obj.Material = mat

    def get_density(self):
        obj = self.doc.getObject('MaterialSolid')
        return Units.Quantity(obj.Material['Density']).getValueAs('kg/m^3')

    def run_analysis(self):
        if self.doc.getObject('ccx_dat_file'):
            self.doc.removeObject('ccx_dat_file')

        self.doc.recompute()

        if self.debug:
            print("Running GMSH mesher ...", end=' ', flush=True)
        mesher = GmshTools(self.doc.getObject('FEMMeshGmsh'))
        err = mesher.create_mesh()
        if err:
            raise ValueError(err)
        obj = self.doc.getObject('FEMMeshGmsh').FemMesh
        if self.debug:
            print(obj.NodeCount, "nodes,",
                  obj.EdgeCount, "edges,",
                  obj.FaceCount, "faces,",
                  obj.VolumeCount, "volumes")

        if self.debug:
            print("Running FEM analysis ...", end=' ', flush=True)
        fea = FemToolsCcx(
            self.doc.getObject('Analysis'),
            self.doc.getObject('SolverCcxTools'))
        fea.purge_results()
        fea.update_objects()
        fea.setup_working_dir()
        fea.setup_ccx()
        err = fea.check_prerequisites()
        if err:
            raise ValueError("FEM error: " + err)
        fea.write_inp_file()
        fea.ccx_run()
        fea.load_results()
        obj = self.doc.getObject('CCX_Results')
        assert obj.ResultType == 'Fem::ResultMechanical'
        if self.debug:
            print("vonMises stress: {:.2f} MPa".format(max(obj.vonMises)))

    def get_vonmises_stress(self) -> float:
        """
        Returns the maximum vonMises stress in mega pascals.
        """
        obj = self.doc.getObject('CCX_Results')
        return max(obj.vonMises)

    def get_tresca_stress(self) -> float:
        """
        Returns the maximum tresca (shear) stress in mega pascals.
        """
        obj = self.doc.getObject('CCX_Results')
        return max(obj.MaxShear)

    def get_displacement(self) -> float:
        """
        Returns the maximum displacement in millimeters.
        """
        obj = self.doc.getObject('CCX_Results')
        return max(obj.DisplacementLengths)

    def has_failed(self) -> bool:
        """
        Returns if the maximum vonMises stress is larger than the tensile strength.
        """
        return self.get_vonmises_stress() >= self.get_tensile_strength()


def run(args=None):
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('model', type=str, metavar='FILE',
                        help='a parametric FreeCAD model of the pressure vessel model')
    args = parser.parse_args(args)

    vessel = PressureVessel(args.model)
    # vessel.print_info()
    vessel.run_analysis()
    vessel.print_info()


if __name__ == '__main__':
    run()
