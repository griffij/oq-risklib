#  -*- coding: utf-8 -*-
#  vim: tabstop=4 shiftwidth=4 softtabstop=4

#  Copyright (c) 2014, GEM Foundation

#  OpenQuake is free software: you can redistribute it and/or modify it
#  under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  OpenQuake is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU Affero General Public License
#  along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.
"""
From Node objects to NRML files and viceversa
------------------------------------------------------

It is possible to save a Node object into a NRML file by using the
function ``write(nodes, output)`` where output is a file
object. If you want to make sure that the generated file is valid
according to the NRML schema just open it in 'w+' mode: immediately
after writing it will be read and validated. It is also possible to
convert a NRML file into a Node object with the routine
``read(node, input)`` where input is the path name of the
NRML file or a file object opened for reading. The file will be
validated as soon as opened.

For instance an exposure file like the following::

  <?xml version='1.0' encoding='utf-8'?>
  <nrml xmlns="http://openquake.org/xmlns/nrml/0.4"
        xmlns:gml="http://www.opengis.net/gml">
    <exposureModel
        id="my_exposure_model_for_population"
        category="population"
        taxonomySource="fake population datasource">

      <description>
        Sample population
      </description>

      <assets>
        <asset id="asset_01" number="7" taxonomy="IT-PV">
            <location lon="9.15000" lat="45.16667" />
        </asset>

        <asset id="asset_02" number="7" taxonomy="IT-CE">
            <location lon="9.15333" lat="45.12200" />
        </asset>
      </assets>
    </exposureModel>
  </nrml>

can be converted as follows:

>> nrml = read(<path_to_the_exposure_file.xml>)

Then subnodes and attributes can be conveniently accessed:

>> nrml.exposureModel.assets[0]['taxonomy']
'IT-PV'
>> nrml.exposureModel.assets[0]['id']
'asset_01'
>> nrml.exposureModel.assets[0].location['lon']
'9.15000'
>> nrml.exposureModel.assets[0].location['lat']
'45.16667'

The Node class provides no facility to cast strings into Python types;
this is a job for the LiteralNode class which can be subclassed and
supplemented by a dictionary of validators.
"""
from __future__ import print_function
import re
import sys
import logging
from openquake.baselib.general import CallableDict
from openquake.baselib.python3compat import unicode, raise_
from openquake.commonlib import valid, writers
from openquake.commonlib.node import (
    node_to_xml, Node, LiteralNode, node_from_elem, striptag,
    parse as xmlparse, iterparse)

NAMESPACE = 'http://openquake.org/xmlns/nrml/0.4'
NRML05 = 'http://openquake.org/xmlns/nrml/0.5'
GML_NAMESPACE = 'http://www.opengis.net/gml'
SERIALIZE_NS_MAP = {None: NAMESPACE, 'gml': GML_NAMESPACE}
PARSE_NS_MAP = {'nrml': NAMESPACE, 'gml': GML_NAMESPACE}


class NRMLFile(object):
    """
    Context-managed output object which accepts either a path or a file-like
    object.

    Behaves like a file.
    """

    def __init__(self, dest, mode='r'):
        self._dest = dest
        self._mode = mode
        self._file = None

    def __enter__(self):
        if isinstance(self._dest, (unicode, bytes)):
            self._file = open(self._dest, self._mode)
        else:
            # assume it is a file-like; don't change anything
            self._file = self._dest
        return self._file

    def __exit__(self, *args):
        self._file.close()


def get_tag_version(nrml_node):
    """
    Extract from a node of kind NRML the tag and the version. For instance
    from '{http://openquake.org/xmlns/nrml/0.4}fragilityModel' one gets
    the pair ('fragilityModel', 'nrml/0.4').
    """
    version, tag = re.search(r'(nrml/[\d\.]+)\}(\w+)', nrml_node.tag).groups()
    return tag, version


nodefactory = CallableDict(keyfunc=striptag)

build = CallableDict(keyfunc=get_tag_version)
# dictionary of functions with at least two arguments, node and fname


def parse(fname, *args):
    """
    Parse a NRML file and return an associated Python object. It works by
    calling nrml.read() and nrml.build() in sequence.
    """
    [node] = read(fname)
    return build(node, fname, *args)


@nodefactory.add('sourceModel', 'simpleFaultRupture', 'complexFaultRupture',
                 'singlePlaneRupture', 'multiPlanesRupture')
class ValidNode(LiteralNode):
    """
    A subclass of :class:`LiteralNode` to be used when parsing sources
    and ruptures from NRML files.
    """
    validators = dict(
        strike=valid.strike_range,
        dip=valid.dip_range,
        rake=valid.rake_range,
        magnitude=valid.positivefloat,
        lon=valid.longitude,
        lat=valid.latitude,
        depth=valid.positivefloat,
        upperSeismoDepth=valid.positivefloat,
        lowerSeismoDepth=valid.positivefloat,
        posList=valid.posList,
        pos=valid.lon_lat,
        aValue=float,
        bValue=valid.positivefloat,
        magScaleRel=valid.mag_scale_rel,
        tectonicRegion=str,
        ruptAspectRatio=valid.positivefloat,
        maxMag=valid.positivefloat,
        minMag=valid.positivefloat,
        binWidth=valid.positivefloat,
        probability=valid.probability,
        hypoDepth=valid.probability_depth,
        occurRates=valid.positivefloats,
        probs_occur=valid.pmf,
        weight=valid.probability,
        alongStrike=valid.probability,
        downDip=valid.probability,
        id=valid.simple_id,
        discretization=valid.compose(valid.positivefloat, valid.nonzero),
        )


nodefactory.add('siteModel')(LiteralNode)


# insuranceLimit and deductible can be either tags or attributes!
def float_or_flag(value, isAbsolute=None):
    """
    Validate the attributes/tags insuranceLimit and deductible
    """
    if isAbsolute is None:  # considering the insuranceLimit attribute
        return valid.positivefloat(value)
    else:
        return valid.boolean(isAbsolute)


@nodefactory.add('exposureModel')
class ExposureDataNode(LiteralNode):
    validators = dict(
        id=valid.simple_id,
        description=valid.utf8,
        name=valid.cost_type,
        type=valid.name,
        insuranceLimit=float_or_flag,
        deductible=float_or_flag,
        occupants=valid.positivefloat,
        value=valid.positivefloat,
        retrofitted=valid.positivefloat,
        number=valid.compose(valid.positivefloat, valid.nonzero),
        lon=valid.longitude,
        lat=valid.latitude,
    )


@nodefactory.add('vulnerabilityModel')
class VulnerabilityNode(LiteralNode):
    """
    Literal Node class used to validate discrete vulnerability functions
    """
    validators = dict(
        vulnerabilitySetID=str,  # any ASCII string is fine
        vulnerabilityFunctionID=str,  # any ASCII string is fine
        assetCategory=str,  # any ASCII string is fine
        # the assetCategory here has nothing to do with the category
        # in the exposure model and it is not used by the engine
        lossCategory=valid.utf8,  # a description field
        IML=valid.IML,
        imls=lambda text, imt: valid.positivefloats(text),
        lr=valid.probability,
        lossRatio=valid.positivefloats,
        coefficientsVariation=valid.positivefloats,
        probabilisticDistribution=valid.Choice('LN', 'BT'),
        dist=valid.Choice('LN', 'BT', 'PM'),
        meanLRs=valid.positivefloats,
        covLRs=valid.positivefloats,
    )


@nodefactory.add('fragilityModel', 'consequenceModel')
class FragilityNode(LiteralNode):
    """
    Literal Node class used to validate fragility functions and consequence
    functions.
    """
    validators = dict(
        id=valid.utf8,  # no constraints on the taxonomy
        format=valid.ChoiceCI('discrete', 'continuous'),
        assetCategory=valid.utf8,
        dist=valid.Choice('LN'),
        mean=valid.positivefloat,
        stddev=valid.positivefloat,
        lossCategory=valid.name,
        poes=lambda text, **kw: valid.positivefloats(text),
        IML=valid.IML,
        minIML=valid.positivefloat,
        maxIML=valid.positivefloat,
        limitStates=valid.namelist,
        description=valid.utf8,
        type=valid.ChoiceCI('lognormal'),
        poEs=valid.probabilities,
        noDamageLimit=valid.NoneOr(valid.positivefloat),
    )

valid_loss_types = valid.Choice('structural', 'nonstructural', 'contents',
                                'business_interruption', 'occupants')


@nodefactory.add('aggregateLossCurve', 'hazardCurves', 'hazardMap')
class CurveNode(LiteralNode):
    validators = dict(
        investigationTime=valid.positivefloat,
        loss_type=valid_loss_types,
        unit=str,
        poEs=valid.probabilities,
        gsimTreePath=lambda v: v.split('_'),
        sourceModelTreePath=lambda v: v.split('_'),
        losses=valid.positivefloats,
        averageLoss=valid.positivefloat,
        stdDevLoss=valid.positivefloat,
        poE=valid.positivefloat,
        IMLs=valid.positivefloats,
        pos=valid.lon_lat,
        IMT=str,
        saPeriod=valid.positivefloat,
        saDamping=valid.positivefloat,
        node=valid.lon_lat_iml,
        quantileValue=valid.positivefloat,
    )


@nodefactory.add('bcrMap')
class BcrNode(LiteralNode):
    validators = dict(
        assetLifeExpectancy=valid.positivefloat,
        interestRate=valid.positivefloat,
        lossCategory=str,
        lossType=valid_loss_types,
        quantileValue=valid.positivefloat,
        statistics=valid.Choice('quantile'),
        unit=str,
        pos=valid.lon_lat,
        aalOrig=valid.positivefloat,
        aalRetr=valid.positivefloat,
        ratio=valid.positivefloat)


def asset_mean_stddev(value, assetRef, mean, stdDev):
    return assetRef, valid.positivefloat(mean), valid.positivefloat(stdDev)


@nodefactory.add('collapseMap')
class CollapseNode(LiteralNode):
    validators = dict(
        pos=valid.lon_lat,
        cf=asset_mean_stddev,
    )


def damage_triple(value, ds, mean, stddev):
    return ds, valid.positivefloat(mean), valid.positivefloat(stddev)


@nodefactory.add('totalDmgDist', 'dmgDistPerAsset', 'dmgDistPerTaxonomy')
class DamageNode(LiteralNode):
    validators = dict(
        damage=damage_triple,
        pos=valid.lon_lat,
        damageStates=valid.namelist,
    )


@nodefactory.add('gmfCollection')
class GmfNode(LiteralNode):
    """
    Class used to convert nodes such as::

     <gmf IMT="PGA" ruptureId="scenario-0000000001" >
        <node gmv="0.365662734506" lat="0.0" lon="0.0"/>
        <node gmv="0.256181251586" lat="0.1" lon="0.0"/>
        <node gmv="0.110685275111" lat="0.2" lon="0.0"/>
     </gmf>

    into LiteralNode objects.
    """
    validators = dict(
        gmv=valid.positivefloat,
        lon=valid.longitude,
        lat=valid.latitude)

# TODO: extend the validation to the following nodes
# see https://bugs.launchpad.net/oq-engine/+bug/1381066
nodefactory.add(
    'disaggMatrices',
    'logicTree',
    'lossCurves',
    'lossFraction',
    'lossMap',
    'stochasticEventSet',
    'stochasticEventSetCollection',
    'uniformHazardSpectra',
    )(LiteralNode)


def read(source, chatty=True):
    """
    Convert a NRML file into a validated LiteralNode object. Keeps
    the entire tree in memory.

    :param source:
        a file name or file object open for reading
    """
    nrml = xmlparse(source).getroot()
    assert striptag(nrml.tag) == 'nrml', nrml.tag
    # extract the XML namespace URL ('http://openquake.org/xmlns/nrml/0.5')
    xmlns = nrml.tag.split('}')[0][1:]
    if xmlns != NRML05 and chatty:
        # for the moment NRML04 is still supported, so we hide the warning
        logging.debug('%s is at an outdated version: %s', source, xmlns)
    subnodes = []
    for elem in nrml:
        nodecls = nodefactory[striptag(elem.tag)]
        try:
            subnodes.append(node_from_elem(elem, nodecls))
        except ValueError as exc:
            raise ValueError('%s of %s' % (exc, source))
    return LiteralNode(
        'nrml', {'xmlns': xmlns, 'xmlns:gml': GML_NAMESPACE},
        nodes=subnodes)


def read_lazy(source, lazytags):
    """
    Convert a NRML file into a validated LiteralNode object. The
    tree is lazy, i.e. you access nodes by iterating on them.

    :param source:
        a file name or file object open for reading
    :param lazytags:
       the name of nodes which subnodes must be read lazily
    :returns:
       a list of nodes; some of them will contain lazy subnodes
    """
    nodes = []
    try:
        for _, el in iterparse(source, remove_comments=True):
            tag = striptag(el.tag)
            if tag in nodefactory:  # NRML tag
                nodes.append(
                    node_from_elem(el, nodefactory[tag], lazy=lazytags))
                el.clear()  # save memory
    except:
        etype, exc, tb = sys.exc_info()
        msg = str(exc)
        if str(source) not in msg:
            msg = '%s in %s' % (msg, source)
        raise_(etype, msg, tb)
    return nodes


def write(nodes, output=sys.stdout, fmt='%10.7E', gml=True):
    """
    Convert nodes into a NRML file. output must be a file
    object open in write mode. If you want to perform a
    consistency check, open it in read-write mode, then it will
    be read after creation and validated.

    :params nodes: an iterable over Node objects
    :params output: a file-like object in write or read-write mode
    """
    root = Node('nrml', nodes=nodes)
    namespaces = {NRML05: ''}
    if gml:
        namespaces[GML_NAMESPACE] = 'gml:'
    with writers.floatformat(fmt):
        node_to_xml(root, output, namespaces)
    if hasattr(output, 'mode') and '+' in output.mode:  # read-write mode
        output.seek(0)
        read(output)  # validate the written file


if __name__ == '__main__':
    import sys
    for fname in sys.argv[1:]:
        print('****** %s ******' % fname)
        print(read(fname).to_str())
        print()
