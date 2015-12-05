#  -*- coding: utf-8 -*-
#  vim: tabstop=4 shiftwidth=4 softtabstop=4

#  Copyright (c) 2014-2015, GEM Foundation

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

import os
import re
import logging
import operator
import collections

import numpy

from openquake.baselib.general import AccumDict, groupby, humansize
from openquake.hazardlib.imt import from_string
from openquake.hazardlib.site import FilteredSiteCollection
from openquake.commonlib.export import export
from openquake.commonlib.oqvalidation import OqParam
from openquake.commonlib.writers import (
    scientificformat, floatformat, write_csv)
from openquake.commonlib import hazard_writers

GMF_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
GMF_WARNING = '''\
There are a lot of ground motion fields; the export will be slow.
Consider canceling the operation and accessing directly %s.'''


class SES(object):
    """
    Stochastic Event Set: A container for 1 or more ruptures associated with a
    specific investigation time span.
    """
    # the ordinal must be > 0: the reason is that it appears in the
    # exported XML file and the schema constraints the number to be
    # nonzero
    def __init__(self, ruptures, investigation_time, ordinal=1):
        self.ruptures = sorted(ruptures, key=operator.attrgetter('tag'))
        self.investigation_time = investigation_time
        self.ordinal = ordinal

    def __iter__(self):
        for sesrup in self.ruptures:
            yield sesrup.export()


class SESCollection(object):
    """
    Stochastic Event Set Collection
    """
    def __init__(self, idx_ses_dict, sm_lt_path, investigation_time=None):
        self.idx_ses_dict = idx_ses_dict
        self.sm_lt_path = sm_lt_path
        self.investigation_time = investigation_time

    def __iter__(self):
        for idx, sesruptures in sorted(self.idx_ses_dict.items()):
            yield SES(sesruptures, self.investigation_time, idx)


@export.add(('sescollection', 'xml'), ('sescollection', 'csv'))
def export_ses_xml(ekey, dstore):
    """
    :param ekey: export key, i.e. a pair (datastore key, fmt)
    :param dstore: datastore object
    """
    fmt = ekey[-1]
    oq = OqParam.from_(dstore.attrs)
    try:
        csm_info = dstore['rlzs_assoc'].csm_info
    except AttributeError:  # for scenario calculators don't export
        return []
    sescollection = dstore['sescollection']
    col_id = 0
    fnames = []
    for sm in csm_info.source_models:
        for trt_model in sm.trt_models:
            sesruptures = list(sescollection[col_id].values())
            col_id += 1
            ses_coll = SESCollection(
                groupby(sesruptures, operator.attrgetter('ses_idx')),
                sm.path, oq.investigation_time)
            smpath = '_'.join(sm.path)
            fname = 'ses-%d-smltp_%s.%s' % (trt_model.id, smpath, fmt)
            dest = os.path.join(dstore.export_dir, fname)
            globals()['_export_ses_' + fmt](dest, ses_coll)
            fnames.append(os.path.join(dstore.export_dir, fname))
    return fnames


def _export_ses_xml(dest, ses_coll):
    writer = hazard_writers.SESXMLWriter(dest, '_'.join(ses_coll.sm_lt_path))
    writer.serialize(ses_coll)


def _export_ses_csv(dest, ses_coll):
    rows = []
    for ses in ses_coll:
        for sesrup in ses:
            rows.append([sesrup.tag, sesrup.seed])
    write_csv(dest, sorted(rows, key=operator.itemgetter(0)))


# #################### export Ground Motion fields ########################## #

class GmfSet(object):
    """
    Small wrapper around the list of Gmf objects associated to the given SES.
    """
    def __init__(self, gmfset, investigation_time, ses_idx):
        self.gmfset = gmfset
        self.investigation_time = investigation_time
        self.stochastic_event_set_id = ses_idx

    def __iter__(self):
        return iter(self.gmfset)

    def __bool__(self):
        return bool(self.gmfset)

    def __str__(self):
        return (
            'GMFsPerSES(investigation_time=%f, '
            'stochastic_event_set_id=%s,\n%s)' % (
                self.investigation_time,
                self.stochastic_event_set_id, '\n'.join(
                    sorted(str(g) for g in self.gmfset))))


def get_ses_idx(tag):
    """
    >>> get_ses_idx("col=00~ses=0007~src=1-3~rup=018-01")
    7
    """
    return int(tag.split('~')[1][4:])


class GroundMotionField(object):
    """
    The Ground Motion Field generated by the given rupture
    """
    def __init__(self, imt, sa_period, sa_damping, rupture_id, gmf_nodes):
        self.imt = imt
        self.sa_period = sa_period
        self.sa_damping = sa_damping
        self.rupture_id = rupture_id
        self.gmf_nodes = gmf_nodes

    def __iter__(self):
        return iter(self.gmf_nodes)

    def __getitem__(self, key):
        return self.gmf_nodes[key]

    def __str__(self):
        # string representation of a _GroundMotionField object showing the
        # content of the nodes (lon, lat an gmv). This is useful for debugging
        # and testing.
        mdata = ('imt=%(imt)s sa_period=%(sa_period)s '
                 'sa_damping=%(sa_damping)s rupture_id=%(rupture_id)s' %
                 vars(self))
        nodes = sorted(map(str, self.gmf_nodes))
        return 'GMF(%s\n%s)' % (mdata, '\n'.join(nodes))


class GroundMotionFieldNode(object):
    # the signature is not (gmv, x, y) because the XML writer expects
    # a location object
    def __init__(self, gmv, loc):
        self.gmv = gmv
        self.location = loc

    def __lt__(self, other):
        """
        A reproducible ordering by lon and lat; used in
        :function:`openquake.commonlib.hazard_writers.gen_gmfs`
        """
        return (self.location.x, self.location.y) < (
            other.location.x, other.location.y)

    def __str__(self):
        """Return lon, lat and gmv of the node in a compact string form"""
        return '<X=%9.5f, Y=%9.5f, GMV=%9.7f>' % (
            self.location.x, self.location.y, self.gmv)


class GmfCollection(object):
    """
    Object converting the parameters

    :param sitecol: SiteCollection
    :rupture_tags: tags of the ruptures
    :gmfs_by_imt: dictionary of GMFs by IMT

    into an object with the right form for the EventBasedGMFXMLWriter.
    Iterating over a GmfCollection yields GmfSet objects.
    """
    def __init__(self, sitecol, ruptures, gmfs, investigation_time):
        self.sitecol = sitecol
        self.ruptures = ruptures
        self.imts = sorted(gmfs[0].dtype.fields)
        self.gmfs_by_imt = {imt: [gmf[imt] for gmf in gmfs]
                            for imt in self.imts}
        self.investigation_time = investigation_time

    def __iter__(self):
        gmfset = collections.defaultdict(list)
        for imt_str in self.imts:
            gmfs = self.gmfs_by_imt[imt_str]
            imt, sa_period, sa_damping = from_string(imt_str)
            for rupture, gmf in zip(self.ruptures, gmfs):
                if hasattr(rupture, 'indices'):  # event based
                    indices = (list(range(len(self.sitecol)))
                               if rupture.indices is None
                               else rupture.indices)
                    sites = FilteredSiteCollection(
                        indices, self.sitecol)
                    ses_idx = get_ses_idx(rupture.tag)
                else:  # scenario
                    sites = self.sitecol
                    ses_idx = 1
                nodes = (GroundMotionFieldNode(gmv, site.location)
                         for site, gmv in zip(sites, gmf))
                gmfset[ses_idx].append(
                    GroundMotionField(
                        imt, sa_period, sa_damping, rupture.tag, nodes))
        for ses_idx in sorted(gmfset):
            yield GmfSet(gmfset[ses_idx], self.investigation_time, ses_idx)


def export_gmf_xml(key, dest, sitecol, ruptures, gmfs, rlz,
                   investigation_time):
    """
    :param key: output_type and export_type
    :param dest: name of the exported file
    :param sitecol: the full site collection
    :param ruptures: an ordered list of ruptures
    :param gmfs: a matrix of ground motion fields of shape (R, N)
    :param rlz: a realization object
    :param investigation_time: investigation time (None for scenario)
    """
    if hasattr(rlz, 'gsim_rlz'):  # event based
        smltpath = '_'.join(rlz.sm_lt_path)
        gsimpath = rlz.gsim_rlz.uid
    else:  # scenario
        smltpath = ''
        gsimpath = rlz.uid
    writer = hazard_writers.EventBasedGMFXMLWriter(
        dest, sm_lt_path=smltpath, gsim_lt_path=gsimpath)
    writer.serialize(
        GmfCollection(sitecol, ruptures, gmfs, investigation_time))
    return {key: [dest]}


def export_gmf_csv(key, dest, sitecol, ruptures, gmfs, rlz,
                   investigation_time):
    """
    :param key: output_type and export_type
    :param dest: name of the exported file
    :param sitecol: the full site collection
    :param ruptures: an ordered list of ruptures
    :param gmfs: an orderd list of ground motion fields
    :param rlz: a realization object
    :param investigation_time: investigation time (None for scenario)
    """
    imts = list(gmfs[0].dtype.fields)
    # the csv file has the form
    # tag,indices,gmvs_imt_1,...,gmvs_imt_N
    rows = []
    for rupture, gmf in zip(ruptures, gmfs):
        try:
            indices = rupture.indices
        except AttributeError:
            indices = sitecol.indices
        if indices is None:
            indices = list(range(len(sitecol)))
        row = [rupture.tag, ' '.join(map(str, indices))] + \
              [gmf[imt] for imt in imts]
        rows.append(row)
    write_csv(dest, rows)
    return {key: [dest]}

# ####################### export hazard curves ############################ #

HazardCurve = collections.namedtuple('HazardCurve', 'location poes')


def export_hazard_curves_csv(key, dest, sitecol, curves_by_imt,
                             imtls, investigation_time=None):
    """
    Export the curves of the given realization into XML.

    :param key: output_type and export_type
    :param dest: name of the exported file
    :param sitecol: site collection
    :param curves_by_imt: dictionary with the curves keyed by IMT
    :param dict imtls: intensity measure types and levels
    :param investigation_time: investigation time
    """
    nsites = len(sitecol)
    # build a matrix of strings with size nsites * (num_imts + 1)
    # the + 1 is needed since the 0-th column contains lon lat
    rows = numpy.empty((nsites, len(imtls) + 1), dtype=object)
    for sid, lon, lat in zip(range(nsites), sitecol.lons, sitecol.lats):
        rows[sid, 0] = '%s %s' % (lon, lat)
    for i, imt in enumerate(curves_by_imt.dtype.names, 1):
        for sid, curve in zip(range(nsites), curves_by_imt[imt]):
            rows[sid, i] = scientificformat(curve, fmt='%11.7E')
    write_csv(dest, rows, header=('lon lat',) + curves_by_imt.dtype.names)
    return {dest: dest}


def hazard_curve_name(dstore, ekey, kind, rlzs_assoc, sampling):
    """
    :param calc_id: the calculation ID
    :param ekey: the export key
    :param kind: the kind of key
    :param rlzs_assoc: a RlzsAssoc instance
    :param sampling: if sampling is enabled or not
    """
    key, fmt = ekey
    prefix = {'hcurves': 'hazard_curve', 'hmaps': 'hazard_map',
              'uhs': 'hazard_uhs'}[key]
    if kind.startswith('rlz-'):
        rlz_no, suffix = re.match('rlz-(\d+)(.*)', kind).groups()
        rlz = rlzs_assoc.realizations[int(rlz_no)]
        fname = build_name(dstore, rlz, prefix + suffix, fmt, sampling)
    elif kind.startswith('mean'):
        fname = dstore.export_path('%s-%s.%s' % (prefix, kind, ekey[1]))
    elif kind.startswith('quantile-'):
        # strip the 7 characters 'hazard_'
        fname = dstore.export_path(
            'quantile_%s-%s.%s' % (prefix[7:], kind[9:], fmt))
    else:
        raise ValueError('Unknown kind of hazard curve: %s' % kind)
    return fname


def build_name(dstore, rlz, prefix, fmt, sampling):
    """
    Build a file name from a realization, by using prefix and extension.

    :param dstore: a DataStore instance
    :param rlz: a realization object
    :param prefix: the prefix to use
    :param fmt: the extension
    :param bool sampling: if sampling is enabled or not

    :returns: relative pathname including the extension
    """
    if hasattr(rlz, 'sm_lt_path'):  # full realization
        smlt_path = '_'.join(rlz.sm_lt_path)
        suffix = '-ltr_%d' % rlz.ordinal if sampling else ''
        fname = '%s-smltp_%s-gsimltp_%s%s.%s' % (
            prefix, smlt_path, rlz.gsim_rlz.uid, suffix, fmt)
    else:  # GSIM logic tree realization used in scenario calculators
        fname = '%s_%s.%s' % (prefix, rlz.uid, fmt)
    return dstore.export_path(fname)


@export.add(('hcurves', 'csv'), ('hmaps', 'csv'), ('uhs', 'csv'))
def export_hcurves_csv(ekey, dstore):
    """
    Exports the hazard curves into several .csv files

    :param ekey: export key, i.e. a pair (datastore key, fmt)
    :param dstore: datastore object
    """
    oq = OqParam.from_(dstore.attrs)
    rlzs_assoc = dstore['rlzs_assoc']
    sitecol = dstore['sitecol']
    key, fmt = ekey
    fnames = []
    for kind, hcurves in dstore[key].items():
        fname = hazard_curve_name(
            dstore, ekey, kind, rlzs_assoc,
            oq.number_of_logic_tree_samples)
        if key == 'uhs':
            export_uhs_csv(ekey, fname, sitecol, hcurves)
        else:
            export_hazard_curves_csv(ekey, fname, sitecol, hcurves, oq.imtls)
        fnames.append(fname)
    return sorted(fnames)


# emulate a Django point
class Location(object):
    def __init__(self, xy):
        self.x, self.y = xy
        self.wkt = 'POINT(%s %s)' % tuple(xy)

HazardCurve = collections.namedtuple('HazardCurve', 'location poes')
HazardMap = collections.namedtuple('HazardMap', 'lon lat iml')


@export.add(('hcurves', 'xml'), ('hcurves', 'geojson'))
def export_hcurves_xml_json(ekey, dstore):
    export_type = ekey[1]
    len_ext = len(export_type) + 1
    oq = OqParam.from_(dstore.attrs)
    sitemesh = dstore['sitemesh'].value
    rlzs_assoc = dstore['rlzs_assoc']
    fnames = []
    writercls = (hazard_writers.HazardCurveGeoJSONWriter
                 if export_type == 'geojson' else
                 hazard_writers.HazardCurveXMLWriter)
    rlzs = iter(rlzs_assoc.realizations)
    for kind, curves in dstore[ekey[0]].items():
        rlz = next(rlzs)
        name = hazard_curve_name(
            dstore, ekey, kind, rlzs_assoc, oq.number_of_logic_tree_samples)
        for imt in oq.imtls:
            fname = name[:-len_ext] + '-' + imt + '.' + export_type
            data = [HazardCurve(Location(site), poes[imt])
                    for site, poes in zip(sitemesh, curves)]
            writer = writercls(fname, investigation_time=oq.investigation_time,
                               imls=oq.imtls[imt],
                               smlt_path='_'.join(rlz.sm_lt_path),
                               gsimlt_path=rlz.gsim_rlz.uid)
            writer.serialize(data)
            fnames.append(fname)
    return sorted(fnames)


@export.add(('hmaps', 'xml'), ('hmaps', 'geojson'))
def export_hmaps_xml_json(ekey, dstore):
    export_type = ekey[1]
    oq = OqParam.from_(dstore.attrs)
    sitemesh = dstore['sitemesh'].value
    rlzs_assoc = dstore['rlzs_assoc']
    fnames = []
    writercls = (hazard_writers.HazardMapGeoJSONWriter
                 if export_type == 'geojson' else
                 hazard_writers.HazardMapXMLWriter)
    rlzs = iter(rlzs_assoc.realizations)
    for kind, maps in dstore[ekey[0]].items():
        rlz = next(rlzs)
        for imt in oq.imtls:
            for i, poe in enumerate(oq.poes):
                suffix = '-%s-%s' % (poe, imt)
                fname = hazard_curve_name(
                    dstore, ekey, kind + suffix, rlzs_assoc,
                    oq.number_of_logic_tree_samples)
                data = [HazardMap(site[0], site[1], poes[imt][i])
                        for site, poes in zip(sitemesh, maps)]
                writer = writercls(
                    fname, investigation_time=oq.investigation_time,
                    imt=imt, poe=poe,
                    smlt_path='_'.join(rlz.sm_lt_path),
                    gsimlt_path=rlz.gsim_rlz.uid)
                writer.serialize(data)
                fnames.append(fname)
    return sorted(fnames)


@export.add(('gmfs', 'xml'), ('gmfs', 'csv'))
def export_gmf(ekey, dstore):
    """
    :param ekey: export key, i.e. a pair (datastore key, fmt)
    :param dstore: datastore object
    """
    sitecol = dstore['sitecol']
    rlzs_assoc = dstore['rlzs_assoc']
    rupture_by_tag = sum(dstore['sescollection'], AccumDict())
    all_tags = dstore['tags'].value
    oq = OqParam.from_(dstore.attrs)
    investigation_time = (None if oq.calculation_mode == 'scenario'
                          else oq.investigation_time)
    samples = oq.number_of_logic_tree_samples
    fmt = ekey[-1]
    gmfs = dstore[ekey[0]]
    nbytes = gmfs.attrs['nbytes']
    logging.info('Internal size of the GMFs: %s', humansize(nbytes))
    if nbytes > GMF_MAX_SIZE:
        logging.warn(GMF_WARNING, dstore.hdf5path)
    fnames = []
    for rlz, gmf_by_idx in zip(
            rlzs_assoc.realizations, rlzs_assoc.combine_gmfs(gmfs)):
        tags = all_tags[list(gmf_by_idx)]
        gmfs = list(gmf_by_idx.values())
        if not gmfs:
            continue
        ruptures = [rupture_by_tag[tag] for tag in tags]
        fname = build_name(dstore, rlz, 'gmf', fmt, samples)
        fnames.append(fname)
        globals()['export_gmf_%s' % fmt](
            ('gmf', fmt), fname, sitecol,
            ruptures, gmfs, rlz, investigation_time)
    return fnames


# not used right now
def export_hazard_curves_xml(key, dest, sitecol, curves_by_imt,
                             imtls, investigation_time):
    """
    Export the curves of the given realization into XML.

    :param key: output_type and export_type
    :param dest: name of the exported file
    :param sitecol: site collection
    :param curves_by_imt: dictionary with the curves keyed by IMT
    :param imtls: dictionary with the intensity measure types and levels
    :param investigation_time: investigation time in years
    """
    mdata = []
    hcurves = []
    for imt_str, imls in sorted(imtls.items()):
        hcurves.append(
            [HazardCurve(site.location, poes)
             for site, poes in zip(sitecol, curves_by_imt[imt_str])])
        imt = from_string(imt_str)
        mdata.append({
            'quantile_value': None,
            'statistics': None,
            'smlt_path': '',
            'gsimlt_path': '',
            'investigation_time': investigation_time,
            'imt': imt[0],
            'sa_period': imt[1],
            'sa_damping': imt[2],
            'imls': imls,
        })
    writer = hazard_writers.MultiHazardCurveXMLWriter(dest, mdata)
    with floatformat('%12.8E'):
        writer.serialize(hcurves)
    return {dest: dest}


def export_uhs_csv(key, dest, sitecol, hmaps):
    """
    Export the scalar outputs.

    :param key: output_type and export_type
    :param dest: file name
    :param sitecol: site collection
    :param hmaps:
        an array N x I x P where N is the number of sites,
        I the number of IMTs of SA type, and P the number of poes
    """
    rows = [[[lon, lat]] + list(row)
            for lon, lat, row in zip(sitecol.lons, sitecol.lats, hmaps)]
    write_csv(dest, rows)
    return {dest: dest}
