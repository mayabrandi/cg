# -*- coding: utf-8 -*-
import os.path
from datetime import datetime
import logging

import click
from path import Path
import ruamel.yaml

from . import apps
from .utils import parse_caseid, check_latest_run

log = logging.getLogger(__name__)


def check_root(context, case_info):
    """Compose and check if root analysis directory for a case exists.

    Aborts the Click CLI context if the family directory doesn't exist.

    Args:
        context (Object): Click context object
        case_info (dict): Parsed case id information

    Returns:
        path: root analysis directory for the family/case
    """
    root_dir = Path(context.obj['analysis_root'])
    family_dir = root_dir.joinpath(case_info['customer_id'], case_info['raw']['family_id'])
    if not family_dir.exists():
        log.error("family directory not found: %s", family_dir)
        context.abort()
    return family_dir


@click.command('mip-config')
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('case_id')
@click.pass_context
def mip_config(context, print_output, case_id):
    """Generate a MIP config from LIMS data."""
    case_info = parse_caseid(case_id)

    log.debug("get config data: %s", case_info['case_id'])
    lims_api = apps.lims.connect(context.obj)
    data = apps.lims.config(lims_api, case_info['customer_id'], case_info['family_id'])

    if case_info['extra']:
        log.info("update config with suffix: %s", case_info['extra'])
        apps.lims.extend_case(data, case_info['extra'])

    raw_output = ruamel.yaml.round_trip_dump(data, indent=4, block_seq_indent=2)
    if print_output:
        click.echo(raw_output.decode())
    else:
        family_dir = check_root(context, case_info)
        config_file = "{}_pedigree.yaml".format(case_info['raw']['family_id'])
        config_path = family_dir.joinpath(config_file)
        with config_path.open('w') as out_handle:
            click.echo(raw_output.decode(), file=out_handle)
        log.info("wrote config to: %s", config_path)


@click.command()
@click.option('--source', '-s', type=click.Choice(['prod', 'archive']), default='prod')
@click.pass_context
def reruns(context, source='prod'):
    """Return reruns marked in Scout (old)."""
    scout_db = apps.scoutprod.connect(context.obj)
    if source == 'prod':
        for scout_case in apps.scoutprod.get_reruns(scout_db):
            click.echo(scout_case['_id'])

    elif source == 'archive':
        scoutold_db = apps.scoutold.connect(context.obj)
        for scout_case in apps.scoutold.get_reruns(scoutold_db):
            case_id = scout_case['_id'].replace('_', '-', 1)
            # lookup requested case in current Scout
            if apps.scoutprod.get_case(scout_db, case_id):
                pass
            else:
                click.echo(case_id)


@click.command('mip-panel')
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('case_id')
@click.pass_context
def mip_panel(context, print_output, case_id):
    """Generate an aggregated panel for MIP."""
    case_info = parse_caseid(case_id)
    lims_api = apps.lims.connect(context.obj)
    samples = lims_api.case(case_info['customer_id'], case_info['family_id'])

    # fetch default panels
    default_panels = set()
    for lims_sample in samples:
        default_panels.update(apps.lims.sample_panels(lims_sample))

    # convert default panels to all panels
    all_panels = apps.lims.convert_panels(case_info['customer_id'], default_panels)
    log.debug("determined panels to use: %s", ', '.join(all_panels))

    adapter = apps.scoutprod.connect_adapter(context.obj)
    bed_lines = apps.scoutprod.export_panels(adapter, all_panels)

    if print_output:
        for bed_line in bed_lines:
            click.echo(bed_line)
    else:
        family_dir = check_root(context, case_info)
        panel_path = family_dir.joinpath('aggregated_master.bed')
        with panel_path.open('w') as out_handle:
            click.echo('\n'.join(bed_lines).decode(), file=out_handle)
        log.info("wrote aggregated gene panel: %s", panel_path)


@click.command()
@click.option('-a', '--answered-out', is_flag=True, help='fill in answered out status')
@click.argument('case_id')
@click.pass_context
def update(context, answered_out, case_id):
    """Fill in information in Housekeeper."""
    if answered_out:
        hk_db = apps.hk.connect(context.obj)
        lims_api = apps.lims.connect(context.obj)
        log.debug("get case from housekeeper")
        hk_case = apps.hk.api.case(case_id)
        log.debug("loop over related samples from most recent run")
        delivery_dates = []
        hk_run = hk_case.current
        for hk_sample in hk_run.samples:
            log.debug("lookup if sample has been delivered in LIMS")
            delivery_date = lims_api.is_delivered(hk_sample.lims_id)
            if delivery_date is None:
                log.warn("sample not delivered: %s", hk_sample.lims_id)
                context.abort()
            delivery_dates.append(delivery_date)
        latest_date = sorted(delivery_dates)[-1]
        log.debug("fillin answered out date in HK")
        hk_run.answeredout_at = datetime.combine(latest_date, datetime.min.time())
        hk_db.commit()
        log.info("run 'answered out' date updated: %s", case_id)


@click.command()
@click.argument('process_id')
@click.pass_context
def check(context, process_id):
    """Check samples in LIMS and optionally update them."""
    admin_db = apps.admin.Application(context.obj)
    lims_api = apps.lims.connect(context.obj)
    samples = list(apps.lims.process_to_samples(lims_api, process_id))
    uniq_tags = set(sample['sample'].udf['Sequencing Analysis'] for sample in samples)
    apptag_map = admin_db.map_apptags(uniq_tags)
    apps.lims.check_samples(lims_api, samples, apptag_map)


@click.command()
@click.option('-s', '--setup/--no-setup', default=True,
              help='perform setup before starting analysis')
@click.option('--execute/--no-execute', default=True, help='skip running MIP')
@click.option('-f', '--force', is_flag=True, help='skip pre-analysis checks')
@click.option('--hg38', is_flag=True, help='run with hg38 settings')
@click.argument('case_id')
@click.pass_context
def start(context, setup, execute, force, hg38, case_id):
    """Start a MIP analysis."""
    case_info = parse_caseid(case_id)
    if setup:
        log.info('generate aggregated gene panel')
        context.invoke(mip_panel, case_id=case_id)
        log.info('generate analysis pedigree')
        context.invoke(mip_config, case_id=case_id)

    log.info("start analysis for: %s", case_id)
    apps.tb.start_analysis(context.obj, case_info, hg38=hg38, force=force, execute=execute)


@click.command()
@click.option('-f', '--force', is_flag=True, help='skip pre-upload checks')
@click.argument('case_id')
@click.pass_context
def coverage(context, force, case_id):
    """Upload coverage for an analysis (latest)."""
    chanjo_db = apps.coverage.connect(context.obj)
    hk_db = apps.hk.connect(context.obj)
    lims_api = apps.lims.connect(context.obj)
    case_info = parse_caseid(case_id)
    latest_run = check_latest_run(hk_db, context, case_info)

    coverage_date = latest_run.extra.coverage_date
    if not force and coverage_date:
        click.echo("Coverage already added for run: {}".format(coverage_date.date()))
    else:
        for sample_data in apps.hk.coverage(hk_db, latest_run):
            chanjo_sample = apps.coverage.sample(sample_data['sample_id'])
            if chanjo_sample:
                log.warn("removing existing sample: %s", chanjo_sample.id)
                apps.coverage.delete(chanjo_db, chanjo_sample)

            lims_sample = lims_api.sample(sample_data['sample_id'])
            log.info("adding coverage for sample: %s", sample_data['sample_id'])
            with open(sample_data['bed_path']) as bed_stream:
                apps.coverage.add(
                    chanjo_db,
                    case_id=case_info['raw']['case_id'],
                    family_name=case_info['raw']['family_id'],
                    sample_id=sample_data['sample_id'],
                    sample_name=lims_sample.name,
                    bed_stream=bed_stream,
                    source=sample_data['bed_path']
                )

        log.info("marking coverage added for case: %s", case_info['raw']['case_id'])
        latest_run.extra.coverage_date = latest_run.analyzed_at
        hk_db.commit()


@click.command()
@click.option('-f', '--force', is_flag=True, help='skip pre-upload checks')
@click.argument('case_id')
@click.pass_context
def genotypes(context, force, case_id):
    """Add VCF genotypes for an analysis run (latest)."""
    genotype_db = apps.gt.connect(context.obj)
    hk_db = apps.hk.connect(context.obj)
    lims_api = apps.lims.connect(context.obj)
    case_info = parse_caseid(case_id)
    latest_run = check_latest_run(hk_db, context, case_info)

    if not force and latest_run.extra.genotype_date:
        click.echo("Genotypes already added for run: {}"
                   .format(latest_run.extra.genotype_date.date()))
    else:
        assets = apps.hk.genotypes(hk_db, latest_run)
        apps.gt.add(genotype_db, assets['bcf_path'], force=force)
        samples_sex = apps.lims.case_sexes(lims_api, case_info['customer_id'],
                                           case_info['family_id'])
        with open(assets['qc_path']) as qcmetrics_stream:
            apps.gt.add_sex(genotype_db, samples_sex, qcmetrics_stream)

        log.info("marking genotypes added for case: %s", case_info['raw']['case_id'])
        latest_run.extra.genotype_date = latest_run.analyzed_at
        hk_db.commit()


@click.command()
@click.option('-f', '--force', is_flag=True, help='skip pre-upload checks')
@click.argument('case_id')
@click.pass_context
def qc(context, force, case_id):
    """Add QC metrics for an anlyais run (latest)."""
    hk_db = apps.hk.connect(context.obj)
    cgstats_db = apps.qc.connect(context.obj)
    case_info = parse_caseid(case_id)
    latest_run = check_latest_run(hk_db, context, case_info)

    if not force and latest_run.extra.qc_date:
        click.echo("QC already added for run: {}".format(latest_run.extra.qc_date.date()))
    else:
        assets = apps.hk.qc(hk_db, latest_run)
        with open(assets['qc_path']) as qc_stream, open(assets['sampleinfo_path']) as si_stream:
            apps.qc.add(cgstats_db, case_info['raw']['case_id'], qc_stream, si_stream, force=force)

        log.info("marking qc added for case: %s", case_info['raw']['case_id'])
        latest_run.extra.qc_date = latest_run.analyzed_at
        hk_db.commit()


@click.command()
@click.option('-f', '--force', is_flag=True, help='skip pre-upload checks')
@click.option('-t', '--threshold', default=5, help='rank score threshold')
@click.argument('case_id')
@click.pass_context
def visualize(context, force, threshold, case_id):
    """Add data to Scout for an analysis run (latest)."""
    hk_db = apps.hk.connect(context.obj)
    scout_db = apps.scoutprod.connect(context.obj)
    case_info = parse_caseid(case_id)
    latest_run = check_latest_run(hk_db, context, case_info)

    if not latest_run.pipeline_version.startswith('v4'):
        log.error("unsupported pipeline version: %s", latest_run.pipeline_version)
        context.abort()

    if not force and latest_run.extra.visualizer_date:
        click.echo("Run already added to scout: {}"
                   .format(latest_run.extra.visualizer_date.date()))
    else:
        config_path = apps.hk.visualize(hk_db, latest_run,
                                        context.obj['housekeeper']['madeline_exe'],
                                        context.obj['housekeeper']['root'])
        with open(config_path) as config_stream:
            config_data = ruamel.yaml.safe_load(config_stream)

        config_data['rank_score_threshold'] = threshold
        apps.scoutprod.add(scout_db, config_data)

        log.info("marking visualize added for case: %s", case_info['raw']['case_id'])
        latest_run.extra.visualizer_date = latest_run.analyzed_at
        hk_db.commit()


@click.command('delivery-report')
@click.argument('case_id')
@click.pass_context
def delivery_report(context, case_id):
    """Generate delivery report for the latest analysis."""
    log.info('connecting to databases')
    hk_db = apps.hk.connect(context.obj)
    lims_api = apps.lims.connect(context.obj)
    cgstats_db = apps.qc.connect(context.obj)
    admin_db = apps.admin.Application(context.obj)
    scout_db = apps.scoutprod.connect(context.obj)
    case_info = parse_caseid(case_id)
    latest_run = check_latest_run(hk_db, context, case_info)

    log.info('fetching data from LIMS')
    case_data = apps.lims.export(lims_api, case_info['customer_id'], case_info['family_id'])
    log.info('fetching data from cgstats')
    case_data = apps.qc.export_run(cgstats_db, case_data)
    log.info('generating report in cgadmin')
    template_out = admin_db.export_report(case_data)

    run_root = apps.hk.rundir(context.obj, latest_run)
    report_file = os.path.join(run_root, 'delivery-report.html')
    log.info("saving report to: %s", report_file)
    click.echo(template_out, file=report_file)
    with click.open_file(report_file, mode='w', encoding='utf-8') as out_handle:
        out_handle.write(template_out)

    log.info("adding report to housekeeper")
    apps.hk.add_asset(hk_db, latest_run, report_file, 'export', archive_type='result')
    apps.scoutprod.report(scout_db, case_info['customer_id'], case_info['family_id'], report_file)


@click.command()
@click.option('-f', '--force', is_flag=True, help='skip pre-upload checks')
@click.argument('case_id')
@click.pass_context
def add(context, force, case_id):
    """Uplaod analysis results (latest) to various databases."""
    hk_db = apps.hk.connect(context.obj)
    admin_db = apps.admin.Application(context.obj)
    case_info = parse_caseid(case_id)
    latest_run = check_latest_run(hk_db, context, case_info)

    if not force and latest_run.delivered_at:
        click.echo("Run already delivered: {}".format(latest_run.delivered_at.date()))
    else:
        log.info("Add coverage")
        context.invoke(coverage, force=force, case_id=case_id)
        log.info("Add genotypes and sex information")
        context.invoke(genotypes, force=force, case_id=case_id)
        log.info("Add QC metrics")
        context.invoke(qc, force=force, case_id=case_id)
        if admin_db.customer(case_info['customer_id']).scout_access:
            log.info("Add case and variants to Scout")
            context.invoke(visualize, force=force, case_id=case_id)
            log.info("Add delivery report to Scout upload")
            context.invoke(delivery_report, case_id=case_id)
