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

import os
import csv

from openquake.baselib.general import AccumDict
from openquake.commonlib.export import export
from openquake.commonlib import risk_writers


@export.add('dmg_dist_per_asset_xml', 'dmg_dist_per_taxonomy_xml',
            'dmg_dist_total_xml', 'collapse_map_xml')
def export_dmg_xml(key, export_dir, damage_states, dmg_data):
    dest = os.path.join(export_dir, key.replace('_xml', '.xml'))
    risk_writers.DamageWriter(damage_states).to_nrml(
        key.replace('_xml', ''), dmg_data, dest)
    return AccumDict({key: dest})


@export.add('agg_loss_csv')
def export_agg_loss_csv(key, export_dir, aggcurves):
    """
    Export aggregate losses in CSV
    """
    dest = os.path.join(export_dir, key.replace('_csv', '.csv'))
    with open(dest, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter='|')
        writer.writerow(['LossType', 'Unit', 'Mean', 'Standard Deviation'])
        writer.writerows(aggcurves)
    return AccumDict({key: dest})