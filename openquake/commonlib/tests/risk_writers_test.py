# coding=utf-8
# Copyright (c) 2010-2014, GEM Foundation.
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import unittest
import io
import itertools
import collections

from openquake.commonlib import nrml_examples
from openquake.commonlib.tests import _utils, check_equal

from openquake.commonlib import risk_writers as writers

HazardMetadata = collections.namedtuple(
    'hazard_metadata',
    'investigation_time statistics quantile sm_path gsim_path')


LOSS_NODE = collections.namedtuple(
    "LossNode", "location asset_ref value std_dev")

BCR_NODE = collections.namedtuple(
    "BCRNode",
    "location asset_ref bcr average_annual_loss_original "
    "average_annual_loss_retrofitted")

LOSS_CURVE = collections.namedtuple(
    "LossCurve",
    "poes losses location asset_ref loss_ratios average_loss stddev_loss")

AGGREGATE_LOSS_CURVE = collections.namedtuple(
    "AggregateLossCurve", "poes losses average_loss stddev_loss")

NO_DAMAGE = writers.DmgState("no_damage", 0)
SLIGHT = writers.DmgState("slight", 1)
MODERATE = writers.DmgState("moderate", 2)
EXTENSIVE = writers.DmgState("extensive", 3)
COMPLETE = writers.DmgState("complete", 4)

DMG_DIST_PER_ASSET = collections.namedtuple(
    "DmgDistPerAsset", "exposure_data dmg_state mean stddev")

DMG_DIST_PER_TAXONOMY = collections.namedtuple(
    "DmgDistPerTaxonomy", "taxonomy dmg_state mean stddev")

DMG_DIST_TOTAL = collections.namedtuple(
    "DmgDistTotal", "dmg_state mean stddev")

COLLAPSE_MAP = collections.namedtuple(
    "CollapseMap", "exposure_data mean stddev")


def remove_file(self):
    'Used in the tearDown methods'
    try:
        os.remove(self.filename)
    except OSError:
        pass


class LossCurveXMLWriterTestCase(unittest.TestCase):

    filename = "loss_curves.xml"

    tearDown = remove_file

    def test_empty_model_not_supported(self):
        writer = writers.LossCurveXMLWriter(
            self.filename, investigation_time=10.0, statistics="mean",
            loss_type="structural")

        self.assertRaises(ValueError, writer.serialize, [])
        self.assertRaises(ValueError, writer.serialize, None)

    def test_serialize_a_model(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml"
      xmlns="http://openquake.org/xmlns/nrml/0.4">
  <lossCurves investigationTime="10.0"
              sourceModelTreePath="b1_b2_b3"
              gsimTreePath="b1_b2" unit="USD" lossType="structural">
    <lossCurve assetRef="asset_1">
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <poEs>1.0 0.5 0.1</poEs>
      <losses>10.0 20.0 30.0</losses>
      <averageLoss>5.0000e+00</averageLoss>
    </lossCurve>
    <lossCurve assetRef="asset_2">
      <gml:Point>
        <gml:pos>2.0 2.5</gml:pos>
      </gml:Point>
      <poEs>1.0 0.3 0.2</poEs>
      <losses>20.0 30.0 40.0</losses>
      <averageLoss>3.0000e+00</averageLoss>
      <stdDevLoss>2.5000e-01</stdDevLoss>
    </lossCurve>
  </lossCurves>
</nrml>
""")
        writer = writers.LossCurveXMLWriter(
            self.filename, investigation_time=10.0,
            source_model_tree_path="b1_b2_b3",
            gsim_tree_path="b1_b2", unit="USD", loss_type="structural")

        data = [
            LOSS_CURVE(
                asset_ref="asset_1", location=writers.Site(1.0, 1.5),
                poes=[1.0, 0.5, 0.1], losses=[10.0, 20.0, 30.0],
                loss_ratios=None, average_loss=5., stddev_loss=None),

            LOSS_CURVE(
                asset_ref="asset_2", location=writers.Site(2.0, 2.5),
                poes=[1.0, 0.3, 0.2], losses=[20.0, 30.0, 40.0],
                loss_ratios=None, average_loss=3., stddev_loss=0.25),
        ]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_an_insured_loss_curve(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml"
      xmlns="http://openquake.org/xmlns/nrml/0.4">
  <lossCurves  insured="True" investigationTime="10.0"
    sourceModelTreePath="b1_b2_b3" gsimTreePath="b1_b2" unit="USD" lossType="structural">
    <lossCurve assetRef="asset_1">
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <poEs>1.0 0.5 0.1</poEs>
      <losses>10.0 20.0 30.0</losses>
      <averageLoss>1.0000e+00</averageLoss>
      <stdDevLoss>5.0000e-01</stdDevLoss>
    </lossCurve>
    <lossCurve assetRef="asset_2">
      <gml:Point>
        <gml:pos>2.0 2.5</gml:pos>
      </gml:Point>
      <poEs>1.0 0.3 0.2</poEs>
      <losses>20.0 30.0 40.0</losses>
      <averageLoss>2.0000e+00</averageLoss>
      <stdDevLoss>1.0000e-01</stdDevLoss>
    </lossCurve>
  </lossCurves>
</nrml>
""")

        writer = writers.LossCurveXMLWriter(
            self.filename,
            investigation_time=10.0, source_model_tree_path="b1_b2_b3",
            gsim_tree_path="b1_b2", unit="USD", insured=True,
            loss_type="structural")

        data = [
            LOSS_CURVE(
                asset_ref="asset_1", location=writers.Site(1.0, 1.5),
                poes=[1.0, 0.5, 0.1], losses=[10.0, 20.0, 30.0],
                loss_ratios=None, average_loss=1., stddev_loss=0.5),

            LOSS_CURVE(
                asset_ref="asset_2", location=writers.Site(2.0, 2.5),
                poes=[1.0, 0.3, 0.2], losses=[20.0, 30.0, 40.0],
                loss_ratios=None, average_loss=2., stddev_loss=0.1),
        ]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_statistics_metadata(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml"
      xmlns="http://openquake.org/xmlns/nrml/0.4">
  <lossCurves investigationTime="10.0"
              statistics="quantile" quantileValue="0.5" lossType="structural">
    <lossCurve assetRef="asset_1">
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <poEs>1.0 0.5 0.1</poEs>
      <losses>10.0 20.0 30.0</losses>
      <lossRatios>0.400 0.600 1.800</lossRatios>
      <averageLoss>0.0000e+00</averageLoss>
      <stdDevLoss>9.0000e-01</stdDevLoss>
    </lossCurve>
  </lossCurves>
</nrml>
""")

        writer = writers.LossCurveXMLWriter(
            self.filename,
            investigation_time=10.0, statistics="quantile",
            quantile_value=0.50, loss_type="structural")

        data = [LOSS_CURVE(
                asset_ref="asset_1", location=writers.Site(1.0, 1.5),
                poes=[1.0, 0.5, 0.1], losses=[10.0, 20.0, 30.0],
                loss_ratios=[0.4, 0.6, 1.8], average_loss=0., stddev_loss=0.9)]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)


class AggregateLossCurveXMLWriterTestCase(unittest.TestCase):

    filename = "aggregate_loss_curves.xml"

    tearDown = remove_file

    def test_empty_model_not_supported(self):
        writer = writers.AggregateLossCurveXMLWriter(
            self.filename, investigation_time=10.0, statistics="mean",
            loss_type="structural")

        self.assertRaises(ValueError, writer.serialize, None)

    def test_serialize_a_model(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml
  xmlns:gml="http://www.opengis.net/gml"
  xmlns="http://openquake.org/xmlns/nrml/0.4">
  <aggregateLossCurve
    investigationTime="10.0"
    sourceModelTreePath="b1_b2_b3"
    gsimTreePath="b1_b2"
    unit="USD"
    lossType="structural">
    <poEs>1.0 0.5 0.1</poEs>
    <losses>10.0000 20.0000 30.0000</losses>
    <averageLoss>3.0000e+00</averageLoss>
    <stdDevLoss>5.0000e-01</stdDevLoss>
  </aggregateLossCurve>
</nrml>
""")

        writer = writers.AggregateLossCurveXMLWriter(
            self.filename,
            investigation_time=10.0, source_model_tree_path="b1_b2_b3",
            gsim_tree_path="b1_b2", unit="USD", loss_type="structural")

        data = AGGREGATE_LOSS_CURVE(
            poes=[1.0, 0.5, 0.1], losses=[10.0, 20.0, 30.0],
            average_loss=3., stddev_loss=0.5)

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_statistics_metadata(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml
  xmlns:gml="http://www.opengis.net/gml"
  xmlns="http://openquake.org/xmlns/nrml/0.4">
  <aggregateLossCurve
    investigationTime="10.0"
    statistics="quantile"
    quantileValue="0.5"
    lossType="structural">
    <poEs>1.0 0.5 0.1</poEs>
    <losses>10.0000 20.0000 30.0000</losses>
    <averageLoss>2.0000e+00</averageLoss>
    <stdDevLoss>5.0000e-01</stdDevLoss>
  </aggregateLossCurve>
</nrml>
""")

        writer = writers.AggregateLossCurveXMLWriter(
            self.filename,
            investigation_time=10.0, statistics="quantile",
            quantile_value=0.50, loss_type="structural")

        data = AGGREGATE_LOSS_CURVE(
            poes=[1.0, 0.5, 0.1], losses=[10.0, 20.0, 30.0],
            average_loss=2., stddev_loss=0.5)

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)


class LossMapWriterTestCase(unittest.TestCase):
    """
    Tests for the XML and GeoJSON loss map writers.
    """

    filename = "loss_map.dat"
    tearDown = remove_file
    data = [
        LOSS_NODE(
            asset_ref="asset_1", location=writers.Site(1.0, 1.5),
            value=15.23, std_dev=None),
        LOSS_NODE(
            asset_ref="asset_2", location=writers.Site(1.0, 1.5),
            value=16.23, std_dev=None),
        LOSS_NODE(
            asset_ref="asset_3", location=writers.Site(2.0, 2.5),
            value=17.23, std_dev=None),
    ]

    def test_empty_model_not_supported_xml(self):
        writer = writers.LossMapXMLWriter(
            self.filename, investigation_time=10.0, poe=0.5,
            statistics="mean", loss_type="structural"
        )

        self.assertRaises(ValueError, writer.serialize, [])
        self.assertRaises(ValueError, writer.serialize, None)

    def test_empty_model_not_supported_geojson(self):
        writer = writers.LossMapGeoJSONWriter(
            self.filename, investigation_time=10.0, poe=0.5,
            statistics="mean", loss_type="structural"
        )

        self.assertRaises(ValueError, writer.serialize, [])
        self.assertRaises(ValueError, writer.serialize, None)

    def test_serialize_a_model_xml(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml"
      xmlns="http://openquake.org/xmlns/nrml/0.4">
  <lossMap investigationTime="10.0" poE="0.8" statistics="mean" lossType="structural">
    <node>
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <loss assetRef="asset_1" value="15.23"/>
      <loss assetRef="asset_2" value="16.23"/>
    </node>
    <node>
      <gml:Point>
        <gml:pos>2.0 2.5</gml:pos>
      </gml:Point>
      <loss assetRef="asset_3" value="17.23"/>
    </node>
  </lossMap>
</nrml>
""")

        writer = writers.LossMapXMLWriter(
            self.filename, investigation_time=10.0, poe=0.8,
            statistics="mean", loss_type="structural"
        )

        writer.serialize(self.data)

        _utils.assert_xml_equal(expected, self.filename)

    maxDiff = None

    def test_serialize_a_model_geojson(self):
        expected = {
            u'features': [
                {u'geometry': {u'coordinates': [1.0, 1.5], u'type': u'Point'},
                 u'properties': {u'asset_ref': u'asset_1', u'loss': 15.23},
                 u'type': u'Feature'},
                {u'geometry': {u'coordinates': [1.0, 1.5], u'type': u'Point'},
                 u'properties': {u'asset_ref': u'asset_2', u'loss': 16.23},
                 u'type': u'Feature'},
                {u'geometry': {u'coordinates': [2.0, 2.5], u'type': u'Point'},
                 u'properties': {u'asset_ref': u'asset_3', u'loss': 17.23},
                 u'type': u'Feature'}],
            u'oqmetadata': {u'investigationTime': u'10.0',
                            u'lossType': u'structural',
                            u'poE': u'0.8',
                            u'statistics': u'mean'},
            u'oqnrmlversion': u'0.4',
            u'oqtype': u'LossMap',
            u'type': u'FeatureCollection'}
        writer = writers.LossMapGeoJSONWriter(
            self.filename, investigation_time=10.0, poe=0.8,
            statistics="mean", loss_type="structural"
        )

        writer.serialize(self.data)

        actual = json.load(open(self.filename))
        self.assertEqual(expected, actual)

    def test_serialize_optional_metadata_xml(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml"
      xmlns="http://openquake.org/xmlns/nrml/0.4">
  <lossMap investigationTime="10.0" poE="0.8" statistics="quantile"
        quantileValue="0.5" lossCategory="economic" unit="USD" lossType="structural">
    <node>
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <loss assetRef="asset_1" mean="15.23" stdDev="2"/>
    </node>
  </lossMap>
</nrml>
""")

        writer = writers.LossMapXMLWriter(
            self.filename,
            investigation_time=10.0, poe=0.80, statistics="quantile",
            quantile_value=0.50, unit="USD", loss_category="economic",
            loss_type="structural"
        )

        data = [LOSS_NODE(
            asset_ref="asset_1", location=writers.Site(1.0, 1.5),
            value=15.23, std_dev=2)]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_optional_metadata_geojson(self):
        expected = {
            u'features': [
                {u'geometry': {u'coordinates': [1.0, 1.5], u'type': u'Point'},
                 u'properties': {u'asset_ref': u'asset_1',
                                 u'loss': 15.23,
                                 u'std_dev': 2.0},
                 u'type': u'Feature'}],
            u'oqmetadata': {u'investigationTime': u'10.0',
                            u'lossCategory': u'economic',
                            u'lossType': u'structural',
                            u'poE': u'0.8',
                            u'quantileValue': u'0.5',
                            u'statistics': u'quantile',
                            u'unit': u'USD'},
            u'oqnrmlversion': u'0.4',
            u'oqtype': u'LossMap',
            u'type': u'FeatureCollection'}

        writer = writers.LossMapGeoJSONWriter(
            self.filename,
            investigation_time=10.0, poe=0.80, statistics="quantile",
            quantile_value=0.50, unit="USD", loss_category="economic",
            loss_type="structural"
        )

        data = [LOSS_NODE(
            asset_ref="asset_1", location=writers.Site(1.0, 1.5),
            value=15.23, std_dev=2)]

        writer.serialize(data)
        actual = json.load(open(self.filename))
        self.assertEqual(expected, actual)

    def test_serialize_using_hazard_realization_xml(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml"
      xmlns="http://openquake.org/xmlns/nrml/0.4">
  <lossMap investigationTime="10.0" poE="0.8"
           sourceModelTreePath="b1|b2" gsimTreePath="b3|b4"
           lossCategory="economic" unit="USD" lossType="structural">
    <node>
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <loss assetRef="asset_1" value="15.23"/>
    </node>
  </lossMap>
</nrml>
""")

        writer = writers.LossMapXMLWriter(
            self.filename,
            investigation_time=10.0, poe=0.80, source_model_tree_path="b1|b2",
            gsim_tree_path="b3|b4", unit="USD", loss_category="economic",
            loss_type="structural")

        data = [LOSS_NODE(asset_ref="asset_1",
                          location=writers.Site(1.0, 1.5),
                          value=15.23, std_dev=None)]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_using_hazard_realization_geojson(self):
        expected = {
            u'features': [
                {u'geometry': {u'coordinates': [1.0, 1.5], u'type': u'Point'},
                 u'properties': {u'asset_ref': u'asset_1',
                                 u'loss': 15.23,
                                 u'std_dev': 2.0},
                 u'type': u'Feature'}],
            u'oqmetadata': {u'gsimTreePath': u'b3|b4',
                            u'investigationTime': u'10.0',
                            u'lossCategory': u'economic',
                            u'lossType': u'structural',
                            u'poE': u'0.8',
                            u'sourceModelTreePath': u'b1|b2',
                            u'unit': u'USD'},
            u'oqnrmlversion': u'0.4',
            u'oqtype': u'LossMap',
            u'type': u'FeatureCollection'}

        writer = writers.LossMapGeoJSONWriter(
            self.filename,
            investigation_time=10.0, poe=0.80, source_model_tree_path="b1|b2",
            gsim_tree_path="b3|b4", unit="USD", loss_category="economic",
            loss_type="structural"
        )

        data = [LOSS_NODE(
            asset_ref="asset_1", location=writers.Site(1.0, 1.5),
            value=15.23, std_dev=2)]

        writer.serialize(data)
        actual = json.load(open(self.filename))
        self.assertEqual(expected, actual)


class LossFractionsWriterTestCase(unittest.TestCase):
    tearDown = remove_file
    filename = "loss_fractions.xml"

    def test_serialize_taxonomies(self):
        expected = file(
            os.path.join(
                os.path.dirname(nrml_examples.__file__),
                "loss-fractions-taxonomies.xml"))

        writers.LossFractionsWriter(
            self.filename, "taxonomy",
            loss_unit="EUR",
            loss_category="building",
            hazard_metadata=HazardMetadata(
                investigation_time=50.,
                statistics=None,
                quantile=None,
                sm_path="b1_b2_b4",
                gsim_path="b1_b2"), poe=0.1, loss_type="structural").serialize(
            dict(RC=(400, 0.2), RM=(1600, 0.8)),
            {(0., 0.): dict(RC=(200, 0.5), RM=(200, 0.5)),
             (1., 1.): dict(RC=(200, 0.25), RM=(1400, 0.75))})

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_taxonomies_from_statistics(self):
        writers.LossFractionsWriter(
            self.filename, "taxonomy",
            loss_unit="EUR",
            loss_category="building",
            hazard_metadata=HazardMetadata(
                investigation_time=50.,
                statistics="quantile",
                quantile=0.3,
                sm_path=None,
                gsim_path=None), poe=None, loss_type="structural").serialize(
            dict(RC=(400, 0.2), RM=(1600, 0.8)),
            {(0., 0.): dict(RC=(200, 0.5), RM=(200, 0.5)),
             (1., 1.): dict(RC=(200, 0.25), RM=(1400, 0.75))})


class BCRMapXMLWriterTestCase(unittest.TestCase):

    filename = "bcr_map.xml"

    tearDown = remove_file

    def test_empty_model_not_supported(self):
        writer = writers.BCRMapXMLWriter(
            self.filename,
            interest_rate=10.0, asset_life_expectancy=0.5, statistics="mean",
            loss_type="structural")

        self.assertRaises(ValueError, writer.serialize, [])
        self.assertRaises(ValueError, writer.serialize, None)

    def test_serialize_a_model(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml" xmlns="http://openquake.org/xmlns/nrml/0.4">
  <bcrMap interestRate="10.0" assetLifeExpectancy="50.0" statistics="mean" lossType="structural">
    <node>
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <bcr assetRef="asset_1" ratio="15.23" aalOrig="10.5" aalRetr="20.5"/>
      <bcr assetRef="asset_2" ratio="16.23" aalOrig="11.5" aalRetr="40.5"/>
    </node>
    <node>
      <gml:Point>
        <gml:pos>2.0 2.5</gml:pos>
      </gml:Point>
      <bcr assetRef="asset_3" ratio="17.23" aalOrig="12.5" aalRetr="10.5"/>
    </node>
  </bcrMap>
</nrml>
""")

        writer = writers.BCRMapXMLWriter(
            self.filename,
            interest_rate=10.0, asset_life_expectancy=50.0, statistics="mean",
            loss_type="structural")

        data = [
            BCR_NODE(
                asset_ref="asset_1", location=writers.Site(1.0, 1.5),
                bcr=15.23, average_annual_loss_original=10.5,
                average_annual_loss_retrofitted=20.5),
            BCR_NODE(
                asset_ref="asset_2", location=writers.Site(1.0, 1.5),
                bcr=16.23, average_annual_loss_original=11.5,
                average_annual_loss_retrofitted=40.5),
            BCR_NODE(
                asset_ref="asset_3", location=writers.Site(2.0, 2.5),
                bcr=17.23, average_annual_loss_original=12.5,
                average_annual_loss_retrofitted=10.5),
        ]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_optional_metadata(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml" xmlns="http://openquake.org/xmlns/nrml/0.4">
  <bcrMap interestRate="10.0" assetLifeExpectancy="50.0" statistics="quantile" quantileValue="0.5" lossCategory="economic" unit="USD" lossType="structural">
    <node>
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <bcr assetRef="asset_1" ratio="15.23" aalOrig="10.5" aalRetr="20.5"/>
    </node>
  </bcrMap>
</nrml>
""")

        writer = writers.BCRMapXMLWriter(
            self.filename,
            interest_rate=10.0, asset_life_expectancy=50.0,
            statistics="quantile", quantile_value=0.50, unit="USD",
            loss_category="economic", loss_type="structural")

        data = [BCR_NODE(
                asset_ref="asset_1", location=writers.Site(1.0, 1.5),
                bcr=15.23, average_annual_loss_original=10.5,
                average_annual_loss_retrofitted=20.5)]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)

    def test_serialize_using_hazard_realization(self):
        expected = io.BytesIO(b"""\
<?xml version='1.0' encoding='UTF-8'?>
<nrml xmlns:gml="http://www.opengis.net/gml" xmlns="http://openquake.org/xmlns/nrml/0.4">
  <bcrMap interestRate="10.0" assetLifeExpectancy="50.0" sourceModelTreePath="b1|b2" gsimTreePath="b1|b2" lossCategory="economic" unit="USD" lossType="structural">
    <node>
      <gml:Point>
        <gml:pos>1.0 1.5</gml:pos>
      </gml:Point>
      <bcr assetRef="asset_1" ratio="15.23" aalOrig="10.5" aalRetr="20.5"/>
    </node>
  </bcrMap>
</nrml>
""")

        writer = writers.BCRMapXMLWriter(
            self.filename,
            interest_rate=10.0, asset_life_expectancy=50.0,
            source_model_tree_path="b1|b2", gsim_tree_path="b1|b2",
            unit="USD", loss_category="economic", loss_type="structural")

        data = [BCR_NODE(
                asset_ref="asset_1", location=writers.Site(1.0, 1.5),
                bcr=15.23, average_annual_loss_original=10.5,
                average_annual_loss_retrofitted=20.5)]

        writer.serialize(data)

        _utils.assert_xml_equal(expected, self.filename)


######################## Scenario Damage Writers #########################

dw = writers.DamageWriter(
    [NO_DAMAGE, SLIGHT, MODERATE, EXTENSIVE, COMPLETE])


class DamageWriterTestCase(unittest.TestCase):

    def test_dmg_total_node(self):
        data = itertools.starmap(DMG_DIST_TOTAL, [
            (NO_DAMAGE, 1.0, 1.6),
            (SLIGHT, 34.8, 18.3),
            (MODERATE, 64.2, 19.8),
            (EXTENSIVE, 64.3, 19.7),
            (COMPLETE, 64.3, 19.7),
        ])
        check_equal(__file__, 'expected_dmg_total.xml',
                    dw.to_nrml('dmg_dist_total', data))

    def test_dmg_per_taxonomy_node(self):
        data = itertools.starmap(DMG_DIST_PER_TAXONOMY, [
            ('RC', NO_DAMAGE, 1.0, 1.6),
            ('RC', SLIGHT, 34.8, 18.3),
            ('RC', MODERATE, 64.2, 19.8),
            ('RC', EXTENSIVE, 64.3, 19.7),
            ('RC', COMPLETE, 64.3, 19.7),
            ('RM', NO_DAMAGE, 1.0, 1.6),
            ('RM', SLIGHT, 34.8, 18.3),
            ('RM', MODERATE, 64.2, 19.8),
            ('RM', EXTENSIVE, 64.3, 19.7),
            ('RM', COMPLETE, 64.3, 19.7),
        ])
        check_equal(__file__, 'expected_dmg_per_taxonomy.xml',
                    dw.to_nrml('dmg_dist_per_taxonomy', data))

    def test_dmg_per_asset_node(self):
        point1 = writers.Site(-116., 41.)
        point2 = writers.Site(-117., 42.)

        e1 = writers.ExposureData('asset_1', point1)
        e2 = writers.ExposureData('asset_2', point2)
        e3 = writers.ExposureData('asset_3', point2)

        data = itertools.starmap(DMG_DIST_PER_ASSET, [
            (e1, NO_DAMAGE, 1.0, 1.6),
            (e1, SLIGHT, 34.8, 18.3),
            (e1, MODERATE, 64.2, 19.8),
            (e1, EXTENSIVE, 64.3, 19.7),
            (e1, COMPLETE, 64.3, 19.7),

            (e2, NO_DAMAGE, 1.0, 1.6),
            (e2, SLIGHT, 34.8, 18.3),
            (e2, MODERATE, 64.2, 19.8),
            (e2, EXTENSIVE, 64.3, 19.7),
            (e2, COMPLETE, 64.3, 19.7),

            (e3, NO_DAMAGE, 1.1, 1.7),
            (e3, SLIGHT, 34.9, 18.4),
            (e3, MODERATE, 64.2, 19.8),
            (e3, EXTENSIVE, 64.3, 19.7),
            (e3, COMPLETE, 64.3, 19.7),
        ])
        check_equal(__file__, 'expected_dmg_per_asset.xml',
                    dw.to_nrml('dmg_dist_per_asset', data))

    def test_collapse_map_node(self):
        point1 = writers.Site(-72.2, 18.)
        point2 = writers.Site(-72.25, 18.)

        e1 = writers.ExposureData('a1', point1)
        e2 = writers.ExposureData('a2', point1)
        e3 = writers.ExposureData('a3', point1)
        e4 = writers.ExposureData('a4', point2)

        data = itertools.starmap(COLLAPSE_MAP, [
            (e1, 1.0, 1.6),
            (e2, 34.8, 18.3),
            (e3, 64.2, 19.8),
            (e4, 64.3, 19.7),
        ])
        check_equal(__file__, 'expected_collapse_map.xml',
                    dw.to_nrml('collapse_map', data))


######################## Hazard Metadata Validation ########################

class HazardMetadataValidationTestCase(unittest.TestCase):

    def test_quantile_metadata_validation(self):
        # `statistics` must be "quantile" or "mean".
        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            statistics="UNKNOWN")

        # when "quantile" is used, `quantile_value` must be
        # specified as well.
        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            statistics="quantile")

        # when "mean" is used, `quantile_value` shouldn't
        # be specified.
        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            statistics="mean", quantile_value=0.50)

        writers.validate_hazard_metadata(quantile_value=0.50,
                                         statistics="quantile")

        writers.validate_hazard_metadata(statistics="mean")

    def test_logic_tree_metadata_validation(self):
        # logic tree parameters must be both specified.
        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            source_model_tree_path="b1|b2")

        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            gsim_tree_path="b1|b2")

        writers.validate_hazard_metadata(source_model_tree_path="b1_b2_b3",
                                         gsim_tree_path="b1_b2")

    def test_logic_tree_or_statistics_metadata_validation(self):
        # logic tree parameters or statistics, not both.
        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            source_model_tree_path="b1|b2", statistics="mean")

        self.assertRaises(
            ValueError, writers.validate_hazard_metadata,
            gsim_tree_path="b1|b2", statistics="mean")

        self.assertRaises(ValueError, writers.validate_hazard_metadata)
