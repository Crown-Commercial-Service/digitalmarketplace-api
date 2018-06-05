import datetime
from itertools import chain, product
import json
import re

import pytest
from sqlalchemy import desc

from dmtestutils.comparisons import AnyStringMatching, AnySupersetOf

from app import db
from app.models import (
    ArchivedService,
    AuditEvent,
    BriefResponse,
    DirectAwardProject,
    DirectAwardSearch,
    Outcome,
    User,
)

from tests.bases import BaseApplicationTest

from ...helpers import FixtureMixin


class TestUpdateOutcome(BaseApplicationTest, FixtureMixin):
    _test_update_outcome_base_scenarios = (
        (
            # other_oc_data
            {},
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Omphalos",
                    "awardValue": "00314.1500",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": True,
                    "award": {
                        "awardingOrganisationName": "Omphalos",
                        "awardValue": "314.15",
                        "startDate": "2020-10-10",
                        "endDate": "2020-11-20",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {
                "completed_at": None,
                "result": "none-suitable",
            },
            # put_values
            {
                "completed": True,
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": True,
                }),
            },
        ),
        (
            # other_oc_data
            {
                "completed_at": None,
                "result": "cancelled",
            },
            # initial_data
            {
                "completed_at": None,
                "result": "none-suitable",
            },
            # put_values
            {
                "completed": True,
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": True,
                }),
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Omphalos",
                    "awardValue": "00314.1500",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": True,
                    "award": {
                        "awardingOrganisationName": "Omphalos",
                        "awardValue": "314.15",
                        "startDate": "2020-10-10",
                        "endDate": "2020-11-20",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            {
                "completed_at": datetime.datetime(2010, 10, 10, 10, 10, 10),
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # initial_data
            {},
            # put_values
            {
                "award": {
                    "awardingOrganisationName": "Omphalos",
                    "awardValue": "00314.1500",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": False,
                    "award": {
                        "awardingOrganisationName": "Omphalos",
                        "awardValue": "314.15",
                        "startDate": "2020-10-10",
                        "endDate": "2020-11-20",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            {
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Omphalos",
                    "awardValue": "00314.1500",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": True,
                    "award": {
                        "awardingOrganisationName": "Omphalos",
                        "awardValue": "314.15",
                        "startDate": "2020-10-10",
                        "endDate": "2020-11-20",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            {},
            # initial_data
            {
                "completed_at": datetime.datetime(2010, 10, 10, 10, 10, 10),
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Incubator",
                    "awardValue": "271271.2",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "award": {
                        "awardingOrganisationName": "Incubator",
                        "awardValue": "271271.20",
                        "startDate": "2020-10-10",
                        "endDate": "2020-11-20",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {
                "completed_at": None,
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # put_values
            {
                "completed": False,
                "award": {
                    "startDate": None,
                },
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": False,
                    "award": {
                        "awardingOrganisationName": "Lambay Freehold",
                        "awardValue": "54321.00",
                        "startDate": None,
                        "endDate": "2011-12-12",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            {},
            # initial_data
            {
                "completed_at": None,
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 5432.1,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # put_values
            {
                "completed": True,
            },
            # expected_status_code
            200,
            # expected_response_data
            {
                "outcome": AnySupersetOf({
                    "completed": True,
                    "award": {
                        "awardingOrganisationName": "Lambay Freehold",
                        "awardValue": "5432.10",
                        "startDate": "2010-12-12",
                        "endDate": "2011-12-12",
                    },
                }),
            },
        ),
        (
            # other_oc_data
            {},
            # initial_data
            {
                "completed_at": None,
                "result": "none-suitable",
            },
            # put_values
            {
                "award": {
                    "awardingOrganisationName": "Talbot de Malahide",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": (
                    "awarding_organisation_name cannot be set for Outcomes with result='none-suitable'."
                    " Attempted to set value 'Talbot de Malahide'"
                ),
            },
        ),
        (
            # other_oc_data
            {
                "completed_at": None,
                "result": "cancelled",
            },
            # initial_data
            {
                "completed_at": datetime.datetime(2010, 3, 3, 3, 3, 3),
                "result": "none-suitable",
            },
            # put_values
            {
                "completed": False,
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": "Can't un-complete outcome",
            },
        ),
        (
            # other_oc_data
            {
                "completed_at": datetime.datetime(2010, 3, 3, 3, 3, 3),
                "result": "cancelled",
            },
            # initial_data
            {
                "completed_at": None,
                "result": "none-suitable",
            },
            # put_values
            {
                "completed": True,
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(
                    r".+ \d+ already has a complete outcome: \d+"
                ),
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {},
            # put_values
            {
                "result": "cancelled",
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(r".*json was not a valid format.*", flags=re.I),
            },
        ),
        (
            # other_oc_data
            {},
            # initial_data
            {},
            # put_values
            {
                "resultOfDirectAward": {
                    "projectId": 321,
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(r".*json was not a valid format.*", flags=re.I),
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                # note "award" section flattened here
                "awardingOrganisationName": "Omphalos",
                "awardValue": "00314.1500",
                "startDate": "2020-10-10",
                "endDate": "2020-11-20",
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(r".*json was not a valid format.*", flags=re.I),
            },
        ),
        (
            # other_oc_data
            {
                "completed_at": datetime.datetime(2010, 10, 10, 10, 10, 10),
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Omphalos",
                    "awardValue": "00314.1500",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(
                    r".+ \d+ already has a complete outcome: \d+"
                ),
            },
        ),
        (
            # other_oc_data
            {
                "completed_at": datetime.datetime(2010, 10, 10, 10, 10, 10),
                "result": "cancelled",
            },
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Omphalos",
                    "awardValue": "00314.1500",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(
                    r".+ \d+ already has a complete outcome: \d+",
                ),
            },
        ),
        (
            # other_oc_data
            {},
            # initial_data
            {
                "completed_at": datetime.datetime(2010, 10, 10, 10, 10, 10),
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # put_values
            {
                "completed": False,
                "award": {
                    "awardingOrganisationName": "Incubator",
                    "awardValue": "271271.2",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": "Can't un-complete outcome",
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {
                "completed_at": datetime.datetime(2010, 10, 10, 10, 10, 10),
                "awarding_organisation_name": "Lambay Freehold",
                "award_value": 54321,
                "start_date": datetime.date(2010, 12, 12),
                "end_date": datetime.date(2011, 12, 12),
            },
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "",
                    "awardValue": "271271.2",
                    "startDate": "2020-10-10",
                    "endDate": "2020-11-20",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(r".*\bawarding_organisation_name\b.*"),
            },
        ),
        (
            # other_oc_data
            {},
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Billy Pitt",
                    "awardValue": "314.15",
                    "startDate": "2020-10-10",
                    "endDate": "2020-20-20",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(r".*\bendDate\b.*"),
            },
        ),
        (
            # other_oc_data
            None,
            # initial_data
            {},
            # put_values
            {
                "completed": True,
                "award": {
                    "awardingOrganisationName": "Martello",
                    "awardValue": "Twelve quid",
                    "startDate": "2020-01-01",
                    "endDate": "2021-12-21",
                },
            },
            # expected_status_code
            400,
            # expected_response_data
            {
                "error": AnyStringMatching(r".*\bawardValue\b.*"),
            },
        ),
    )

    @pytest.mark.parametrize(
        (
            "other_oc_brief_based",
            "initial_brief_based",
            "other_oc_data",
            "initial_data",
            "put_values",
            "expected_status_code",
            "expected_response_data",
        ),
        tuple(chain(
            (   # we reproduce here the variants in _test_update_outcome_base_scenarios, once for Briefs, once
                # for Projects
                (f_t, f_t,) + variant_params
                for f_t, variant_params in product((False, True,), _test_update_outcome_base_scenarios)
            ),
            (   # and also include some with mixed target-types
                (
                    # other_oc_brief_based
                    False,
                    # initial_brief_based
                    True,
                    # other_oc_data
                    {
                        "completed_at": datetime.datetime(2007, 7, 7, 7, 7, 7),
                        "result": "none-suitable",
                    },
                    # initial_data
                    {
                        "completed_at": None,
                        "result": "cancelled",
                    },
                    # put_values
                    {
                        "completed": True,
                    },
                    # expected_status_code
                    200,
                    # expected_response_data
                    {
                        "outcome": AnySupersetOf({
                            "completed": True,
                        }),
                    },
                ),
                (
                    # other_oc_brief_based
                    True,
                    # initial_brief_based
                    False,
                    # other_oc_data
                    {
                        "completed_at": datetime.datetime(2007, 7, 7, 7, 7, 7),
                        "awarding_organisation_name": "Lambay Freehold",
                        "award_value": 54321,
                        "start_date": datetime.date(2010, 12, 12),
                        "end_date": datetime.date(2011, 12, 12),
                    },
                    # initial_data
                    {},
                    # put_values
                    {
                        "completed": True,
                        "award": {
                            "awardingOrganisationName": "Omphalos",
                            "awardValue": "00314.1500",
                            "startDate": "2020-10-10",
                            "endDate": "2020-11-20",
                        },
                    },
                    # expected_status_code
                    200,
                    # expected_response_data
                    {
                        "outcome": AnySupersetOf({
                            "completed": True,
                            "award": {
                                "awardingOrganisationName": "Omphalos",
                                "awardValue": "314.15",
                                "startDate": "2020-10-10",
                                "endDate": "2020-11-20",
                            },
                        }),
                    },
                ),
            ),
        )),
        ids=(lambda val: "EMPTYDCT" if val == {} else None),
    )
    def test_update_outcome_scenarios(
        self,
        other_oc_brief_based,
        initial_brief_based,
        other_oc_data,
        initial_data,
        put_values,
        expected_status_code,
        expected_response_data,
    ):
        """
        A number of arguments control the background context this test is run in and the parameters PUT to the endpoint.
        Not all of the combinations make sense together and a caller should not expect a test to pass with a nonsensical
        combination of arguments

        :param other_oc_brief_based:   whether the "other", existing Outcome should be Brief-based as opposed to
                                       Direct Award-based
        :param initial_brief_based:    whether the target Outcome should initially be set up to be Brief-based as
                                       opposed to Direct Award-based
        :param other_oc_data:          field values to set up the "other" Outcome with, ``None`` for no "other"
                                       Outcome to be created
        :param initial_data:           field values to initially set up the target Outcome with
        :param put_values:             payload dictionary to be PUT to the target endpoint (without the
                                       ``outcome`` wrapper)
        :param expected_status_code:
        :param expected_response_data:
        """
        user_id = self.setup_dummy_user(id=1, role='buyer')
        self.setup_dummy_suppliers(3)

        project = None
        search = None
        chosen_archived_service = other_archived_service = None
        if not (other_oc_brief_based and initial_brief_based):
            # create required objects for direct award-based Outcome
            self.setup_dummy_services(3, model=ArchivedService)

            project = DirectAwardProject(
                name="Lambay Island",
                users=[User.query.get(user_id)],
            )
            db.session.add(project)

            search = DirectAwardSearch(
                project=project,
                created_by=user_id,
                active=True,
                search_url="http://nothing.nowhere",
            )
            db.session.add(search)

            for archived_service in db.session.query(ArchivedService).filter(
                ArchivedService.service_id.in_(("2000000000", "2000000001",))
            ).all():
                search.archived_services.append(archived_service)

            chosen_archived_service, other_archived_service = search.archived_services[:2]
        # else skip creating these to save time

        brief = None
        chosen_brief_response = other_brief_response = None
        if other_oc_brief_based or initial_brief_based:
            # create required objects for brief-based Outcome
            brief = self.setup_dummy_brief(status="closed", user_id=user_id, data={})
            chosen_brief_response, other_brief_response = (BriefResponse(
                brief=brief,
                supplier_id=i,
                submitted_at=datetime.datetime.utcnow(),
                data={},
            ) for i in (1, 2,))
            db.session.add(chosen_brief_response)
            db.session.add(other_brief_response)
        # else skip creating these to save time

        other_outcome = None
        if other_oc_data is not None:
            # create "other" Outcome for our target one to potentially clash with
            other_outcome = Outcome(
                **({"brief": brief} if other_oc_brief_based else {"direct_award_project": project}),
                **({
                    "result": other_oc_data.get("result", "awarded"),
                    **({
                        "brief_response": other_brief_response,
                    } if other_oc_brief_based else {
                        "direct_award_search": search,
                        "direct_award_archived_service": other_archived_service,
                    }),
                } if other_oc_data.get("result", "awarded") == "awarded" else {"result": other_oc_data["result"]}),
                **{k: v for k, v in (other_oc_data or {}).items() if k not in ("completed_at", "result",)},
            )
            if "completed_at" in other_oc_data:
                other_outcome.completed_at = other_oc_data["completed_at"]
            db.session.add(other_outcome)

        # create our target Outcome in its initial state
        outcome = Outcome(
            **({"brief": brief} if initial_brief_based else {"direct_award_project": project}),
            **({
                "result": initial_data.get("result", "awarded"),
                **({
                    "brief_response": chosen_brief_response,
                } if initial_brief_based else {
                    "direct_award_search": search,
                    "direct_award_archived_service": chosen_archived_service,
                }),
            } if initial_data.get("result", "awarded") == "awarded" else {"result": initial_data["result"]}),
            **{k: v for k, v in (initial_data or {}).items() if k not in ("completed_at", "result",)},
        )
        if "completed_at" in initial_data:
            # can only set completed_at after other fields have been set
            outcome.completed_at = initial_data["completed_at"]
        db.session.add(outcome)

        # must assign ids before we can lock project
        db.session.flush()
        if project:
            project.locked_at = datetime.datetime.now()

        # make a concrete note of these so we don't have to fetch them back from the database after the request,
        # potentially getting back values which have been inadvertantly changed
        outcome_external_id = outcome.external_id
        project_external_id = project and project.external_id
        search_id = search and search.id
        chosen_archived_service_id = chosen_archived_service and chosen_archived_service.id
        chosen_archived_service_service_id = chosen_archived_service and chosen_archived_service.service_id
        brief_id = brief and brief.id
        chosen_brief_response_id = chosen_brief_response and chosen_brief_response.id
        audit_event_count = AuditEvent.query.count()
        db.session.commit()

        # keep an nice concrete representation for later comparison
        outcome_serialization_before = outcome.serialize()

        res = self.client.put(
            f"/outcomes/{outcome.external_id}",
            data=json.dumps({
                "updated_by": "lord.talbot@example.com",
                "outcome": put_values,
            }),
            content_type="application/json",
        )
        assert res.status_code == expected_status_code
        response_data = json.loads(res.get_data())
        assert response_data == expected_response_data

        # allow these to be re-used in this session, "refreshed"
        db.session.add_all(x for x in (outcome, project, search, chosen_archived_service,) if x is not None)
        db.session.expire_all()

        if res.status_code != 200:
            # assert change wasn't made, audit event wasn't added
            assert outcome.serialize() == outcome_serialization_before
            assert AuditEvent.query.count() == audit_event_count
        else:
            # an additional check of values we should be able to figure out the "correct" values for
            assert response_data == {
                "outcome": {
                    "id": outcome_external_id,
                    "result": initial_data.get("result", "awarded"),
                    "completed": (
                        bool(outcome_serialization_before.get("completedAt"))
                        or put_values.get("completed") is True
                    ),
                    "completedAt": (
                        outcome_serialization_before.get("completedAt")
                        or (
                            AnyStringMatching(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z")
                            if put_values.get("completed") else None
                        )
                    ),
                    **({
                        "resultOfFurtherCompetition": {
                            "briefId": brief_id,
                            **({
                                "briefResponseId": chosen_brief_response_id,
                            } if initial_data.get("result", "awarded") == "awarded" else {}),
                        },
                    } if initial_brief_based else {
                        "resultOfDirectAward": {
                            "projectId": project_external_id,
                            **({
                                "searchId": search_id,
                                "serviceId": chosen_archived_service_service_id,
                                "archivedServiceId": chosen_archived_service_id,
                            } if initial_data.get("result", "awarded") == "awarded" else {})
                        },
                    }),
                    **({"award": AnySupersetOf({})} if initial_data.get("result", "awarded") == "awarded" else {}),
                }
            }

            # check changes actually got committed
            assert response_data == {
                "outcome": outcome.serialize(),
            }

            # check audit event(s) were saved
            expect_complete_audit_event = put_values.get("completed") is True and not initial_data.get("completed_at")
            n_expected_new_audit_events = 2 if expect_complete_audit_event else 1

            assert AuditEvent.query.count() == audit_event_count + n_expected_new_audit_events
            # grab those most recent (1 or) 2 audit events from the db, re-sorting them to be in a predictable order -
            # we don't care whether the complete_outcome or update_outcome comes out of the db first
            audit_events = sorted(
                db.session.query(AuditEvent).order_by(
                    desc(AuditEvent.created_at),
                    desc(AuditEvent.id),
                )[:n_expected_new_audit_events],
                key=lambda ae: ae.type,
                reverse=True,
            )

            assert audit_events[0].type == "update_outcome"
            assert audit_events[0].object is outcome
            assert audit_events[0].acknowledged is False
            assert audit_events[0].acknowledged_at is None
            assert not audit_events[0].acknowledged_by
            assert audit_events[0].user == "lord.talbot@example.com"
            assert audit_events[0].data == put_values

            if expect_complete_audit_event:
                assert audit_events[1].type == "complete_outcome"
                assert audit_events[1].created_at == audit_events[0].created_at == outcome.completed_at
                assert audit_events[1].object is outcome
                assert audit_events[1].acknowledged is False
                assert audit_events[1].acknowledged_at is None
                assert not audit_events[1].acknowledged_by
                assert audit_events[1].user == "lord.talbot@example.com"
                assert audit_events[1].data == {}

    def test_nonexistent_outcome(self):
        res = self.client.put(
            f"/outcomes/314159",
            data=json.dumps({
                "updated_by": "lord.talbot@example.com",
                "outcome": {
                    "completed": True,
                },
            }),
            content_type="application/json",
        )
        assert res.status_code == 404
        assert json.loads(res.get_data()) == {
            "error": "Outcome 314159 not found",
        }
