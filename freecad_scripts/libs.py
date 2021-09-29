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
        PATH = os.path.dirname(lib)
        if PATH not in sys.path:
            sys.path.append(PATH)
        break
else:
    raise ValueError("FreeCAD library was not found!")

import FreeCAD                              # noqa
from FreeCAD import Units                   # noqa
from femtools.ccxtools import FemToolsCcx   # noqa
from femmesh.gmshtools import GmshTools     # noqa
