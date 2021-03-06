# -*- coding: utf-8 -*-
import datetime as dt
from typing import List

from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Query

from cg.store import models


class FindHandler:

    def customer(self, internal_id: str) -> models.Customer:
        """Fetch a customer by internal id from the store."""
        return self.Customer.query.filter_by(internal_id=internal_id).first()

    def customers(self) -> List[models.Customer]:
        """Fetch all customers."""
        return self.Customer.query

    def user(self, email: str) -> models.User:
        """Fetch a user from the store."""
        return self.User.query.filter_by(email=email).first()

    def family(self, internal_id: str) -> models.Family:
        """Fetch a family by internal id from the database."""
        return self.Family.query.filter_by(internal_id=internal_id).first()

    def families(self, *, customer: models.Customer=None, query: str=None,
                 action: str=None) -> List[models.Family]:
        """Fetch all families."""
        records = self.Family.query
        records = records.filter_by(customer=customer) if customer else records
        records = records.filter(or_(
            models.Family.name.like(f"%{query}%"),
            models.Family.internal_id.like(f"%{query}%"),
        )) if query else records
        records = records.filter_by(action=action) if action else records
        return records.order_by(models.Family.created_at.desc())

    def find_family(self, customer: models.Customer, name: str) -> models.Family:
        """Find a family by family name within a customer."""
        return self.Family.query.filter_by(customer=customer, name=name).first()

    def sample(self, internal_id: str) -> models.Sample:
        """Fetch a sample by lims id."""
        return self.Sample.query.filter_by(internal_id=internal_id).first()

    def samples(self, *, customer: models.Customer=None, query: str=None) -> List[models.Sample]:
        records = self.Sample.query
        records = records.filter_by(customer=customer) if customer else records
        records = records.filter(or_(
            models.Sample.name.like(f"%{query}%"),
            models.Sample.internal_id.like(f"%{query}%"),
        )) if query else records
        return records.order_by(models.Sample.created_at.desc())

    def find_sample(self, customer: models.Customer, name: str) -> List[models.Sample]:
        """Find samples within a customer."""
        return self.Sample.query.filter_by(customer=customer, name=name)

    def application(self, tag: str) -> models.Application:
        """Fetch an application from the store."""
        return self.Application.query.filter_by(tag=tag).first()

    def applications(self, *, category=None, archived=None):
        """Fetch all applications."""
        records = self.Application.query
        if category:
            records = records.filter_by(prep_category=category)
        if archived is not None:
            records = records.filter_by(is_archived=archived)
        return records

    def application_version(self, application: models.Application,
                            version: int) -> models.ApplicationVersion:
        """Fetch an application version."""
        query = self.ApplicationVersion.query.filter_by(application=application, version=version)
        return query.first()

    def latest_version(self, tag: str) -> models.ApplicationVersion:
        """Fetch the latest application version for an application tag."""
        application_obj = self.Application.query.filter_by(tag=tag).first()
        return application_obj.versions[-1] if application_obj else None

    def panel(self, abbrev):
        """Find a panel by abbreviation."""
        return self.Panel.query.filter_by(abbrev=abbrev).first()

    def analyses(self, *, family: models.Family=None, before: dt.datetime=None) -> Query:
        """Fetch multiple analyses."""
        records = self.Analysis.query
        if family:
            records = records.filter(models.Analysis.family == family)
        if before:
            subq = self.Analysis.query.\
                join(models.Analysis.family).\
                group_by(models.Family.id).\
                with_entities(models.Analysis.id, func.max(models.Analysis.started_at).label('started_at')).subquery()
            records = records.join(
                subq,
                and_(self.Analysis.id == subq.c.id, self.Analysis.started_at == subq.c.started_at)
            ).filter(models.Analysis.started_at < before)
        return records

    def analysis(self, family: models.Family, started_at: dt.datetime) -> models.Analysis:
        """Fetch an analysis."""
        return self.Analysis.query.filter_by(family=family, started_at=started_at).first()

    def flowcells(self, *, status: str=None, family: models.Family=None,
                  query: str=None) -> List[models.Flowcell]:
        """Fetch all flowcells."""
        records = self.Flowcell.query
        if family:
            records = (
                records
                .join(models.Flowcell.samples, models.Sample.links)
                .filter(models.FamilySample.family == family)
            )
        if status:
            records = records.filter_by(status=status)
        if query:
            records = records.filter(models.Flowcell.name.like(f"%{query}%"))
        return records.order_by(models.Flowcell.sequenced_at.desc())

    def flowcell(self, name: str) -> models.Flowcell:
        """Fetch a flowcell."""
        return self.Flowcell.query.filter_by(name=name).first()

    def link(self, family_id: str, sample_id: str) -> models.FamilySample:
        """Find a link between a family and a sample."""
        return (
            self.FamilySample.query
            .join(models.FamilySample.family, models.FamilySample.sample)
            .filter(
                models.Family.internal_id == family_id,
                models.Sample.internal_id == sample_id
            )
            .first()
        )

    def family_samples(self, family_id: str) -> models.FamilySample:
        """Find the samples of a family."""
        return (
            self.FamilySample.query
            .join(models.FamilySample.family, models.FamilySample.sample)
            .filter(
                models.Family.internal_id == family_id,
            )
            .all()
        )

    def pools(self, *, customer: models.Customer):
        """Fetch all the pools."""
        records = self.Pool.query
        records = records.filter_by(customer=customer) if customer else records
        return records

    def pool(self, pool_id: int):
        """Fetch a pool."""
        return self.Pool.get(pool_id)
    
    def deliveries(self):
        """Fetch all deliveries."""
        query = self.Delivery.query
        return query
