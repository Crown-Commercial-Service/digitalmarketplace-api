import datetime
import decimal

from sqlalchemy.orm import validates, backref
from sqlalchemy.sql.expression import (
    and_ as sql_and,
    case as sql_case,
)

from dmutils.errors.api import ValidationError
from dmutils.formats import DATE_FORMAT, DATETIME_FORMAT

from app import db
from app.utils import random_positive_external_id


class Outcome(db.Model):
    __tablename__ = "outcomes"

    RESULT_CHOICES = (
        "awarded",
        "cancelled",
        "none-suitable",
    )

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.BigInteger, nullable=False, default=random_positive_external_id, unique=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    awarding_organisation_name = db.Column(db.String, nullable=True)
    # should be enough scale to represent up to £1b - 1p
    award_value = db.Column(db.Numeric(11, 2), nullable=True)

    result = db.Column(db.String, nullable=False)

    direct_award_project_id = db.Column(
        db.Integer,
        db.ForeignKey('direct_award_projects.id'),
        nullable=True,
    )
    direct_award_search_id = db.Column(
        db.Integer,
        db.ForeignKey('direct_award_searches.id'),
        nullable=True,
    )
    direct_award_archived_service_id = db.Column(
        db.Integer,
        db.ForeignKey('archived_services.id'),
        nullable=True,
    )

    # NOTE though Outcome currently has the *ability* to be associated with a Brief/BriefResponse, at time of
    # writing this is not yet *used* for reporting brief awards - those are still using their own mechanism, but should
    # be ported over to this mechanism as soon as time allows.
    brief_id = db.Column(
        db.Integer,
        db.ForeignKey('briefs.id'),
        nullable=True,
    )
    brief_response_id = db.Column(
        db.Integer,
        db.ForeignKey('brief_responses.id'),
        nullable=True,
    )

    # The following constraints enforce this general scheme:
    # All Outcomes must point at either a DirectAwardProject OR a Brief. If the Outcome's "result" is
    # "awarded", then a DirectAwardProject-based Outcome must also point at the DirectAwardProject's active
    # search and "winning" archived_service_id or a Brief-based Outcome must also point at the winning
    # BriefResponse. Only one "completed" Outcome can point at its target (DirectAwardProject or Brief) at once.
    #
    # Overlapping compound foreign keys are used to ensure the correctness of the
    # DirectAwardProject-DirectAwardSearch-ArchivedService and Brief-BriefResponse chains.
    #
    # These particular restrictions were chosen to be enforced at a database level because they're all part of an
    # interrelated system of rules related to cross-table relationships. Contraints which only deal with intra-row
    # rules can be handled safely (enough) with app-side validation.

    __table_args__ = (
        db.CheckConstraint(sql_case(
            # if awarded, the "null-ness" of direct_award_project_id, direct_award_search_id &
            # direct_award_archived_service_id must be the same
            (result == "awarded", sql_and(
                (direct_award_project_id.is_(None) == direct_award_search_id.is_(None)),
                (direct_award_project_id.is_(None) == direct_award_archived_service_id.is_(None)),
            )),
            # if not awarded, we shouldn't have direct_award_search_id or direct_award_archived_service_id set
            else_=sql_and(direct_award_search_id.is_(None), direct_award_archived_service_id.is_(None)),
        ), name="ck_outcomes_direct_award_keys_nullable"),
        db.CheckConstraint(sql_case(
            # if awarded, the "null-ness" of brief_response_id and brief_id must be the same
            (result == "awarded", brief_response_id.is_(None) == brief_id.is_(None),),
            # if not awarded, brief_response_id should not be set
            else_=brief_response_id.is_(None),
        ), name="ck_outcomes_brief_keys_nullable"),
        # the "null-ness" of direct_award_project_id and brief_id must *never* be the same
        db.CheckConstraint(
            (direct_award_project_id.is_(None) != brief_id.is_(None)),
            name="ck_outcomes_either_brief_xor_direct_award",
        ),
        # only one completed award can point at a DirectAwardProject at once
        db.Index(
            "idx_outcomes_completed_direct_award_project_unique",
            direct_award_project_id,
            postgresql_where=(completed_at.isnot(None)),
            unique=True,
        ),
        # only one completed award can point at a Brief at once
        db.Index(
            "idx_outcomes_completed_brief_unique",
            brief_id,
            postgresql_where=(completed_at.isnot(None)),
            unique=True,
        ),
        # direct_award_archived_service_id must actually be a result of the given DirectAwardSearch
        db.ForeignKeyConstraint(
            (direct_award_archived_service_id, direct_award_search_id,),
            ("direct_award_search_result_entries.archived_service_id", "direct_award_search_result_entries.search_id",),
            name="fk_outcomes_da_service_id_da_search_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        # direct_award_search_id must actually belong the given DirectAwardProject
        db.ForeignKeyConstraint(
            (direct_award_search_id, direct_award_project_id,),
            ("direct_award_searches.id", "direct_award_searches.project_id",),
            name="fk_outcomes_da_search_id_da_project_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        # brief_response_id must actually belong to the given Brief
        db.ForeignKeyConstraint(
            (brief_response_id, brief_id,),
            ("brief_responses.id", "brief_responses.brief_id",),
            name="fk_outcomes_brief_response_id_brief_id",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    direct_award_project = db.relationship(
        "DirectAwardProject",
        foreign_keys=direct_award_project_id,
        # named as such to be explicit that this includes incomplete "outcomes"
        backref="outcomes_all",
    )
    direct_award_search = db.relationship(
        "DirectAwardSearch",
        foreign_keys=direct_award_search_id,
        # named as such to be explicit that this includes incomplete "outcomes"
        backref="outcomes_all",
    )
    direct_award_search_result_entry = db.relationship(
        "DirectAwardSearchResultEntry",
        foreign_keys=(direct_award_search_id, direct_award_archived_service_id,),
        uselist=False,
        # being able to write to this relationship could cause ambiguities with the other relationships that also
        # use some of their keys
        viewonly=True,
        # named as such to be explicit that this includes incomplete "outcomes"
        backref=backref("outcomes_all", viewonly=True),
    )
    direct_award_archived_service = db.relationship(
        "ArchivedService",
        foreign_keys=direct_award_archived_service_id,
        # named as such to be explicit that this includes incomplete "outcomes"
        backref="outcomes_all",
    )

    brief_response = db.relationship(
        "BriefResponse",
        foreign_keys=brief_response_id,
        # named as such to be explicit that this includes incomplete "outcomes"
        backref="outcomes_all",
    )
    brief = db.relationship(
        "Brief",
        foreign_keys=brief_id,
        # named as such to be explicit that this includes incomplete "outcomes"
        backref="outcomes_all",
    )

    def update_from_json(self, update_data):
        award_dict = update_data.get("award", {})
        if not isinstance(award_dict, dict):
            raise ValidationError(f"'award' expected to be a dictionary")
        for k, v in award_dict.items():
            key_mapping = {
                "startDate": "start_date",
                "endDate": "end_date",
                "awardingOrganisationName": "awarding_organisation_name",
                "awardValue": "award_value",
            }
            if k in key_mapping:
                if k == "awardValue":
                    try:
                        v = decimal.Decimal(v) if v is not None else None
                    except decimal.InvalidOperation:
                        raise ValidationError(f"Failed to parse {v!r} as decimal for field {k!r}")
                elif k in ("startDate", "endDate",):
                    if v is not None:
                        try:
                            v = datetime.datetime.strptime(v, DATE_FORMAT).date()
                        except ValueError as e:
                            raise ValidationError(f"Failed to parse {v!r} as date for field {k!r}: {e.args[0]}")

                setattr(self, key_mapping[k], v)

    def serialize(self):
        return {
            "id": self.external_id,
            "completed": self.completed_at is not None,
            "completedAt": self.completed_at.strftime(DATETIME_FORMAT) if self.completed_at is not None else None,
            "result": self.result,
            **(
                {
                    "resultOfDirectAward": {
                        "project": {
                            "id": self.direct_award_project.external_id,
                        },
                        **(
                            {
                                # heavily abbreviated versions of these objects' serializations
                                "search": {
                                    "id": self.direct_award_search_id,
                                },
                                "archivedService": {
                                    "id": self.direct_award_archived_service_id,
                                    "service": {
                                        "id": self.direct_award_archived_service.service_id,
                                    },
                                },
                            } if self.result == "awarded" else {}
                        ),
                    },
                } if self.direct_award_project_id is not None else {}
            ),
            **(
                {
                    "resultOfFurtherCompetition": {
                        "brief": {
                            "id": self.brief_id,
                        },
                        **(
                            {
                                "briefResponse": {
                                    "id": self.brief_response_id,
                                },
                            } if self.result == "awarded" else {}
                        )
                    },
                } if self.brief_id is not None else {}
            ),
            **(
                {
                    "award": {
                        "startDate": self.start_date and self.start_date.strftime(DATE_FORMAT),
                        "endDate": self.end_date and self.end_date.strftime(DATE_FORMAT),
                        "awardingOrganisationName": self.awarding_organisation_name,
                        # don't risk json representing this as a float
                        "awardValue": str(self.award_value) if self.award_value is not None else None,
                    },
                } if self.result == "awarded" else {}
            ),
        }

    @validates(
        "start_date",
        "end_date",
        "awarding_organisation_name",
        "award_value",
    )
    def _validates_data_complete_if_completed_at(self, key, value):
        if key == "award_value":
            if value is not None and value < 0:
                raise ValidationError(f"{key} must be greater than or equal to zero, got {value!r}")

        if self.completed_at and self.result == "awarded" and value in (None, "",):
            raise ValidationError(
                f"{key} cannot be None or empty if Outcome with result={self.result!r} is 'completed'."
                f" Received {value!r}"
            )

        if self.result not in (None, "awarded",) and value is not None:
            raise ValidationError(
                f"{key} cannot be set for Outcomes with result={self.result!r}. Attempted to set value {value!r}"
            )

        return value

    @validates("completed_at", "result")
    def _validates_completed_at_data_complete_if_set(self, key, value):
        if key == "result" and value not in self.RESULT_CHOICES:
            raise ValidationError(f"{value!r} is not a valid choice for field {key!r}")

        result = value if key == "result" else self.result
        completed_at = value if key == "completed_at" else self.completed_at
        if result == "awarded" and completed_at is not None:
            failures = ", ".join(
                "{}={}".format(fkey, repr(getattr(self, fkey)))
                for fkey in (
                    "start_date",
                    "end_date",
                    "awarding_organisation_name",
                    "award_value",
                )
                if (getattr(self, fkey) in (None, "",))
            )
            if failures:
                raise ValidationError(
                    f"Outcome with result={result!r} cannot be 'completed' with None or empty data fields,"
                    f" but {failures}"
                )
        if result not in (None, "awarded",):
            failures = ", ".join(
                "{}={}".format(fkey, repr(getattr(self, fkey)))
                for fkey in (
                    "start_date",
                    "end_date",
                    "awarding_organisation_name",
                    "award_value",
                )
                if getattr(self, fkey) is not None
            )
            if failures:
                raise ValidationError(
                    f"Outcomes with result={result!r} cannot have award-related data fields set, but {failures}"
                )
        return value
