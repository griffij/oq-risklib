# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2016 GEM Foundation
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from openquake.commonlib import sap, nrml


def tidy(fnames):
    """
    Reformat a NRML file in a canonical form. That also means reducing the
    precision of the floats to a standard value. If the file is invalid,
    a clear error message is shown.
    """
    for fname in fnames:
        try:
            nodes = nrml.read(fname).nodes
        except ValueError as err:
            print(err)
            return
        with open(fname + '.bak', 'w') as f:
            f.write(open(fname).read())
        with open(fname, 'w') as f:
            nrml.write(nodes, f)
        print('Reformatted %s, original left in %s.bak' % (fname, fname))

parser = sap.Parser(tidy)
parser.arg('fnames', 'NRML file name', nargs='+')
