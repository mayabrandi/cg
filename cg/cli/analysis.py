# -*- coding: utf-8 -*-
import logging

import click

from cg.apps import hk, tb, scoutapi, lims
from cg.meta.analysis import AnalysisAPI
from cg.store import Store

LOG = logging.getLogger(__name__)
PRIORITY_OPTION = click.option('-p', '--priority', type=click.Choice(['low', 'normal', 'high']))
EMAIL_OPTION = click.option('-e', '--email', help='email to send errors to')


@click.group(invoke_without_command=True)
@PRIORITY_OPTION
@EMAIL_OPTION
@click.option('-f', '--family', 'family_id', help='family to prepare and start an analysis for')
@click.pass_context
def analysis(context, priority, email, family_id):
    """Prepare and start a MIP analysis for a FAMILY_ID."""
    context.obj['db'] = Store(context.obj['database'])
    hk_api = hk.HousekeeperAPI(context.obj)
    scout_api = scoutapi.ScoutAPI(context.obj)
    lims_api = lims.LimsAPI(context.obj)
    context.obj['tb'] = tb.TrailblazerAPI(context.obj)
    context.obj['api'] = AnalysisAPI(
        db=context.obj['db'],
        hk_api=hk_api,
        tb_api=context.obj['tb'],
        scout_api=scout_api,
        lims_api=lims_api,
    )

    if context.invoked_subcommand is None:
        if family_id is None:
            LOG.error('provide a family')
            context.abort()

        # check everything is okey
        family_obj = context.obj['db'].family(family_id)
        if family_obj is None:
            LOG.error(f"{family_id} not found")
            context.abort()
        is_ok = context.obj['api'].check(family_obj)
        if not is_ok:
            LOG.warning(f"{family_obj.internal_id}: not ready to start")
            # commit the updates to request flowcells
            context.obj['db'].commit()
        else:
            # execute the analysis!
            context.invoke(config, family_id=family_id)
            context.invoke(link, family_id=family_id)
            context.invoke(panel, family_id=family_id)
            context.invoke(start, family_id=family_id, priority=priority, email=email)


@analysis.command()
@click.option('-d', '--dry', is_flag=True, help='print config to console')
@click.argument('family_id')
@click.pass_context
def config(context, dry, family_id):
    """Generate a config for the FAMILY_ID."""
    family_obj = context.obj['db'].family(family_id)
    config_data = context.obj['api'].config(family_obj)
    if dry:
        print(config_data)
    else:
        out_path = context.obj['tb'].save_config(config_data)
        LOG.info(f"saved config to: {out_path}")


@analysis.command()
@click.option('-f', '--family', 'family_id', help='link all samples for a family')
@click.argument('sample_id', required=False)
@click.pass_context
def link(context, family_id, sample_id):
    """Link FASTQ files for a SAMPLE_ID."""
    if family_id and (sample_id is None):
        # link all samples in a family
        family_obj = context.obj['db'].family(family_id)
        link_objs = family_obj.links
    elif sample_id and (family_id is None):
        # link sample in all its families
        sample_obj = context.obj['db'].sample(sample_id)
        link_objs = sample_obj.links
    elif sample_id and family_id:
        # link only one sample in a family
        link_objs = [context.obj['db'].link(family_id, sample_id)]
    else:
        LOG.error('provide family and/or sample')
        context.abort()

    for link_obj in link_objs:
        LOG.info(f"{link_obj.sample.internal_id}: link FASTQ files")
        context.obj['api'].link_sample(link_obj)


@analysis.command()
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('family_id')
@click.pass_context
def panel(context, print_output, family_id):
    """Write aggregated gene panel file."""
    family_obj = context.obj['db'].family(family_id)
    bed_lines = context.obj['api'].panel(family_obj)
    if print_output:
        for bed_line in bed_lines:
            print(bed_line)
    else:
        context.obj['tb'].write_panel(family_id, bed_lines)


@analysis.command()
@PRIORITY_OPTION
@EMAIL_OPTION
@click.argument('family_id')
@click.pass_context
def start(context: click.Context, family_id: str, priority: str=None, email: str=None):
    """Start the analysis pipeline for a family."""
    family_obj = context.obj['db'].family(family_id)
    if family_obj is None:
        LOG.error(f"{family_id}: family not found")
        context.abort()
    if context.obj['tb'].analyses(family=family_obj.internal_id, temp=True).first():
        LOG.warning(f"{family_obj.internal_id}: analysis already running")
    else:
        context.obj['api'].start(family_obj, priority=priority, email=email)


@analysis.command()
@click.pass_context
def auto(context: click.Context):
    """Start all analyses that are ready for analysis."""
    for family_obj in context.obj['db'].families_to_analyze():
        LOG.info(f"{family_obj.internal_id}: start analysis")
        priority = ('high' if family_obj.high_priority else
                    ('low' if family_obj.low_priority else 'normal'))
        try:
            context.invoke(analysis, priority=priority, family_id=family_obj.internal_id)
        except tb.MipStartError as error:
            LOG.exception(error.message)
