# -*- coding: utf-8 -*-
from flask_admin.contrib.sqla import ModelView


class BaseView(ModelView):
    pass


class CustomerView(BaseView):
    column_exclude_list = [
        'agreement_date',
        'agreement_registration',
        'organisation_number',
        'invoice_address',
        'delivery_contact',
        'invoice_contact',
    ]
    column_searchable_list = ['internal_id', 'name', 'primary_contact']
    column_filters = ['priority', 'scout_access']
    column_editable_list = ['name', 'scout_access', 'primary_contact', 'priority']


class UserView(BaseView):
    column_searchable_list = ['name', 'email', 'customer.internal_id']
    column_filters = ['customer.internal_id']
    column_editable_list = ['customer', 'is_admin']
    create_modal = True
    edit_modal = True


class ApplicationView(BaseView):
    column_exclude_list = [
        'minimum_order',
        'sample_amount',
        'sample_volume',
        'details',
        'limitations',
        'percent_kth',
        'created_at',
        'updated_at',
        'category',
    ]
    column_searchable_list = ['tag', 'prep_category']
    column_filters = ['prep_category', 'is_accredited']
    column_editable_list = ['description', 'is_accredited', 'target_reads', 'comment',
                            'prep_category', 'sequencing_depth', 'is_external']
    form_excluded_columns = ['category']


class ApplicationVersionView(BaseView):
    column_exclude_list = [
        'created_at',
        'updated_at',
    ]
    column_searchable_list = ['application.tag']
    column_filters = ['version', 'application.tag']
    column_editable_list = ['valid_from']
    edit_modal = True


class PanelView(BaseView):
    column_searchable_list = ['customer.internal_id', 'name', 'abbrev']
    column_filters = ['customer.internal_id']
    column_editable_list = ['current_version', 'name']
    create_modal = True
    edit_modal = True


class FamilyView(BaseView):
    column_exclude_list = ['created_at']
    column_searchable_list = ['internal_id', 'name', 'customer.internal_id']
    column_filters = ['customer.internal_id', 'priority', 'action']
    column_editable_list = ['action']


class SampleView(BaseView):
    column_searchable_list = ['internal_id', 'name', 'ticket_number', 'customer.internal_id']
    column_filters = ['customer.internal_id', 'sex', 'application_version.application']
    column_editable_list = ['sex']


class FamilySampleView(BaseView):
    column_searchable_list = ['family.internal_id', 'family.name', 'sample.internal_id']
    column_filters = ['status']
    column_editable_list = ['status']
    create_modal = True
    edit_modal = True


class FlowcellView(BaseView):
    column_searchable_list = ['name']
    column_filters = ['sequencer_type', 'sequencer_name']


class AnalysisView(BaseView):
    column_searchable_list = ['family.internal_id', 'family.name']
    column_filters = ['pipeline', 'pipeline_version', 'is_primary']
    column_editable_list = ['is_primary']
