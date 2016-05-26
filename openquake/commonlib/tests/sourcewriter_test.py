# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2015-2016 GEM Foundation
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

import os
import copy
import unittest
import tempfile
from openquake.commonlib.sourcewriter import write_source_model
from openquake.commonlib.sourceconverter import SourceConverter
from openquake.commonlib.source import SourceModelParser
from openquake.commonlib import nrml_examples

NONPARAM = os.path.join(os.path.dirname(__file__), 'data',
                        'nonparametric-source.xml')
MIXED = os.path.join(os.path.dirname(nrml_examples.__file__),
                     'source_model/mixed.xml')

ALT_MFDS = os.path.join(
    os.path.dirname(nrml_examples.__file__),
    'source_model/alternative-mfds_4test.xml')


class SourceWriterTestCase(unittest.TestCase):

    def check_round_trip(self, fname):
        parser = SourceModelParser(SourceConverter(50., 1., 10, 0.1, 10.))
        sources = parser.parse_sources(fname)
        fd, name = tempfile.mkstemp(suffix='.xml')
        with os.fdopen(fd, 'w'):
            write_source_model(name, sources, 'Test Source Model')
        if open(name).read() != open(fname).read():
            raise Exception('Different files: %s %s' % (name, fname))
        os.remove(name)

    def test_mixed(self):
        self.check_round_trip(MIXED)

    def test_nonparam(self):
        self.check_round_trip(NONPARAM)

    def test_alt_mfds(self):
        self.check_round_trip(ALT_MFDS)


class DeepcopyTestCase(unittest.TestCase):
    def test_is_writeable(self):
        parser = SourceModelParser(SourceConverter(50., 1., 10, 0.1, 10.))
        [sf, cf] = map(copy.deepcopy, parser.parse_sources(ALT_MFDS))
        # there are a SimpleFaultSource and a CharacteristicFaultSource
        fd, fname = tempfile.mkstemp(suffix='.xml')
        with os.fdopen(fd, 'w'):
            write_source_model(fname, [sf, cf], 'Test Source Model')
        # NB: without Node.__deepcopy__ the serialization would fail
        # with a RuntimeError: maximum recursion depth exceeded while
        # calling a Python object
