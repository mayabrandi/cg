# -*- coding: utf-8 -*-
import gzip
import logging
import re
from typing import List

from requests.exceptions import HTTPError

from cg.apps import tb, hk, scoutapi, lims
from cg.store import models, Store

LOG = logging.getLogger(__name__)

COLLABORATORS = ('cust000', 'cust002', 'cust003', 'cust004', 'cust042')
MASTER_LIST = ('ENDO', 'EP', 'IEM', 'IBMFS', 'mtDNA', 'MIT', 'PEDHEP', 'OMIM-AUTO',
               'PIDCAD', 'PID', 'SKD', 'NMD', 'ATX', 'CTD', 'ID', 'SPG', 'Ataxi', 'AD-HSP')
COMBOS = {
    'DSD': ('DSD', 'HYP', 'SEXDIF', 'SEXDET'),
    'CM': ('CNM', 'CM'),
    'Horsel': ('Horsel', '141217', '141201'),
}
CAPTUREKIT_MAP = {'Agilent Sureselect CRE': 'agilent_sureselect_cre.v1',
                  'SureSelect CRE': 'agilent_sureselect_cre.v1',
                  'Agilent Sureselect V5': 'agilent_sureselect.v5',
                  'SureSelect Focused Exome': 'agilent_sureselect_focusedexome.v1',
                  'other': 'agilent_sureselect_cre.v1'}


class AnalysisAPI():

    def __init__(self, db: Store, hk_api: hk.HousekeeperAPI, scout_api: scoutapi.ScoutAPI,
                 tb_api: tb.TrailblazerAPI, lims_api: lims.LimsAPI):
        self.db = db
        self.tb = tb_api
        self.hk = hk_api
        self.scout = scout_api
        self.lims = lims_api

    def check(self, family_obj: models.Family):
        """Check stuff before starting the analysis."""
        flowcells = self.db.flowcells(family=family_obj)
        statuses = []
        for flowcell_obj in flowcells:
            LOG.debug(f"{flowcell_obj.name}: checking flowcell")
            statuses.append(flowcell_obj.status)
            if flowcell_obj.status == 'removed':
                LOG.info(f"{flowcell_obj.name}: requesting removed flowcell")
                flowcell_obj.status = 'requested'
            elif flowcell_obj.status != 'ondisk':
                LOG.warning(f"{flowcell_obj.name}: {flowcell_obj.status}")
        return all(status == 'ondisk' for status in statuses)

    def start(self, family_obj: models.Family, **kwargs):
        """Start the analysis."""
        if kwargs.get('priority') is None:
            if family_obj.priority == 0:
                kwargs['priority'] = 'low'
            elif family_obj.priority > 1:
                kwargs['priority'] = 'high'
            else:
                kwargs['priority'] = 'normal'

        # skip MIP evaluation of QC criteria if any sample is downsampled/external
        for link_obj in family_obj.links:
            downsampled = isinstance(link_obj.sample.downsampled_to, int)
            external = link_obj.sample.application_version.application.is_external
            if downsampled or external:
                LOG.info(f"{link_obj.sample.internal_id}: downsampled/external - skip evaluation")
                kwargs['skip_evaluation'] = True
                break

        self.tb.start(family_obj.internal_id, **kwargs)
        # mark the family as running
        family_obj.action = 'running'
        self.db.commit()

    def config(self, family_obj: models.Family) -> dict:
        """Make the MIP config."""
        data = self.build_config(family_obj)
        config_data = self.tb.make_config(data)
        return config_data

    def build_config(self, family_obj: models.Family) -> dict:
        """Fetch data for creating a MIP config file."""
        data = {
            'family': family_obj.internal_id,
            'default_gene_panels': family_obj.panels,
            'samples': [],
        }
        for link in family_obj.links:
            sample_data = {
                'sample_id': link.sample.internal_id,
                'analysis_type': link.sample.application_version.application.analysis_type,
                'sex': link.sample.sex,
                'phenotype': link.status,
                'expected_coverage': link.sample.application_version.application.sequencing_depth,
            }
            if sample_data['analysis_type'] in ('tgs', 'wes'):
                if link.sample.capture_kit:
                    # set the capture kit from status: key or custom file name
                    mip_capturekit = CAPTUREKIT_MAP.get(link.sample.capture_kit)
                    sample_data['capture_kit'] = mip_capturekit or link.sample.capture_kit
                else:
                    if link.sample.downsampled_to:
                        LOG.debug(f"{link.sample.name}: downsampled sample, skipping")
                    else:
                        try:
                            capture_kit = self.lims.capture_kit(link.sample.internal_id)
                            if capture_kit is None or capture_kit == 'NA':
                                LOG.warning(f"{link.sample.internal_id}: capture kit not found")
                            else:
                                sample_data['capture_kit'] = CAPTUREKIT_MAP[capture_kit]
                        except HTTPError:
                            LOG.warning(f"{link.sample.internal_id}: not found (LIMS)")
            if link.mother:
                sample_data['mother'] = link.mother.internal_id
            if link.father:
                sample_data['father'] = link.father.internal_id
            data['samples'].append(sample_data)
        return data

    def link_sample(self, link_obj: models.FamilySample):
        """Link FASTQ files for a sample."""
        file_objs = self.hk.files(bundle=link_obj.sample.internal_id, tags=['fastq'])
        files = []
        for file_obj in file_objs:
            # figure out flowcell name from header
            with gzip.open(file_obj.full_path) as handle:
                header_line = handle.readline().decode()
                part1, part2 = header_line.split(' ', 1)
                lane = part1.split(':')[3]
                flowcell = part1.split(':')[2]
                readnumber = part2.split(':')[0]

            data = {
                'path': file_obj.full_path,
                'lane': int(lane),
                'flowcell': flowcell,
                'read': int(readnumber),
                'undetermined': ('_Undetermined_' in file_obj.path),
            }
            # look for tile identifier (HiSeq X runs)
            matches = re.findall(r'-l[1-9]t([1-9]{2})_', file_obj.path)
            if len(matches) > 0:
                data['flowcell'] = f"{data['flowcell']}-{matches[0]}"
            files.append(data)

        self.tb.link(
            family=link_obj.family.internal_id,
            sample=link_obj.sample.internal_id,
            analysis_type=link_obj.sample.application_version.application.analysis_type,
            files=files,
        )

    def panel(self, family_obj: models.Family) -> List[str]:
        """Create the aggregated panel file."""
        all_panels = self.convert_panels(family_obj.customer.internal_id, family_obj.panels)
        bed_lines = self.scout.export_panels(all_panels)
        return bed_lines

    @staticmethod
    def convert_panels(customer: str, default_panels: List[str]) -> List[str]:
        """Convert between default panels and all panels included in gene list."""
        if customer in COLLABORATORS:
            # check if all default panels are part of master list
            if all(panel in MASTER_LIST for panel in default_panels):
                return MASTER_LIST

        # the rest are handled the same way
        all_panels = set(default_panels)

        # fill in extra panels if selection is part of a combo
        for panel in default_panels:
            if panel in COMBOS:
                for extra_panel in COMBOS[panel]:
                    all_panels.add(extra_panel)

        # add OMIM to every panel choice
        all_panels.add('OMIM-AUTO')

        return list(all_panels)
