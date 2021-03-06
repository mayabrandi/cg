# -*- coding: utf-8 -*-
import logging

import ruamel.yaml
import click
from dateutil.parser import parse as parse_date

from cg.apps import tb, hk
from cg.store import Store

LOG = logging.getLogger(__name__)


@click.group()
@click.pass_context
def clean(context):
    """Remove stuff."""
    context.obj['db'] = Store(context.obj['database'])
    context.obj['tb'] = tb.TrailblazerAPI(context.obj)


@clean.command()
@click.option('-d', '--dry', is_flag=True, help='print config to console')
@click.option('-y', '--yes', is_flag=True, help='skip confirmation')
@click.argument('sample_info', type=click.File('r'))
@click.pass_context
def mip(context, dry, yes, sample_info):
    """Remove analysis output."""
    raw_data = ruamel.yaml.safe_load(sample_info)
    data = context.obj['tb'].parse_sampleinfo(raw_data)

    family = data['family']
    family_obj = context.obj['db'].family(family)
    if family_obj is None:
        LOG.error(f"{family}: family not found")
        context.abort()

    analysis_obj = context.obj['db'].analysis(family_obj, data['date'])
    if analysis_obj is None:
        LOG.error(f"{family} - {data['date']}: analysis not found")
        context.abort()

    try:
        context.obj['tb'].delete_analysis(family, data['date'], yes=yes)
    except ValueError as error:
        LOG.error(f"{family}: {error.args[0]}")
        context.abort()


@clean.command()
@click.option('-y', '--yes', is_flag=True, help='skip confirmation')
@click.argument('before_str')
@click.pass_context
def auto(context: click.Context, before_str: str, yes: bool=False):
    """Automatically clean up "old" analyses."""
    before = parse_date(before_str)
    old_analyses = context.obj['db'].analyses(before=before)
    for status_analysis in old_analyses:
        family_id = status_analysis.family.internal_id
        LOG.info(f"{family_id}: clean up analysis output")
        tb_analysis = context.obj['tb'].find_analysis(
            family=family_id,
            started_at=status_analysis.started_at,
            status='completed'
        )

        if tb_analysis is None:
            LOG.warning(f"{family_id}: analysis not found in Trailblazer")
            continue
        elif tb_analysis.is_deleted:
            LOG.warning(f"{family_id}: analysis already deleted")
            continue
        elif context.obj['tb'].analyses(family=family_id, temp=True).count() > 0:
            LOG.warning(f"{family_id}: family already re-started")
            continue

        LOG.info(f"{family_id}: cleaning MIP output")
        sampleinfo_path = context.obj['tb'].get_sampleinfo(tb_analysis)
        context.invoke(mip, yes=yes, sample_info=open(sampleinfo_path, 'r'))
