# -*- coding: UTF-8 -*-
from datetime import datetime
from itertools import chain, repeat
import mock
import pytest
from flask import json
from urllib.parse import urlencode
from freezegun import freeze_time

from dmapiclient.audit import AuditTypes

from app import db
from app.models import AuditEvent
from app.models import Supplier, Service
from tests.bases import BaseApplicationTest
from tests.helpers import FixtureMixin

from dmtestutils.api_model_stubs import AuditEventStub


class BaseTestAuditEvents(BaseApplicationTest, FixtureMixin):
    @staticmethod
    def audit_event(
        user=0,
        type=AuditTypes.supplier_update,
        db_object=None,
        data={"request": "data"},
        *,
        created_at=None
    ):
        e = AuditEvent(audit_type=type, db_object=db_object, user=user, data=data,)
        if created_at:
            e.created_at = created_at
        return e

    def add_audit_event(
        self,
        user=0,
        type=AuditTypes.supplier_update,
        db_object=None,
        data={"request": "data"},
        *,
        created_at=None
    ):
        ae = self.audit_event(user, type, db_object, data, created_at=created_at)
        db.session.add(ae)
        db.session.commit()
        return ae.id

    def add_audit_events(
        self,
        number,
        type=AuditTypes.supplier_update,
        db_object=None,
        *,
        created_at=None
    ):
        ids = []
        for user_id in range(number):
            ids.append(
                self.add_audit_event(
                    user=user_id, type=type, db_object=db_object, created_at=created_at
                )
            )
        return ids

    def add_audit_events_with_db_object(self):
        self.setup_dummy_suppliers(3)
        events = []
        suppliers = Supplier.query.all()
        for supplier in suppliers:
            event = AuditEvent(AuditTypes.contact_update, "rob", {}, supplier)
            events.append(event)
            db.session.add(event)
        db.session.commit()
        return tuple(event.id for event in events)

    def add_audit_events_by_param_tuples(self, service_audit_event_params, supplier_audit_event_params):
        # some migrations create audit events, but we want to start with a clean slate
        AuditEvent.query.delete()
        service_ids = [service.id for service in db.session.query(Service.id).order_by(Service.id).all()]
        supplier_ids = [supplier.id for supplier in db.session.query(Supplier.id).order_by(Supplier.id).all()]

        audit_events = []

        for (ref_model, ref_model_ids), (obj_id, audit_type, created_at, acknowledged_at) in chain(
            zip(repeat((Service, service_ids,)), service_audit_event_params),
            zip(repeat((Supplier, supplier_ids,)), supplier_audit_event_params),
        ):
            ae = AuditEvent(audit_type, "henry.flower@example.com", {}, ref_model(id=ref_model_ids[obj_id]))
            ae.created_at = created_at
            ae.acknowledged_at = acknowledged_at
            ae.acknowledged = bool(acknowledged_at)
            ae.acknowledged_by = acknowledged_at and "c.p.mccoy@example.com"
            db.session.add(ae)
            audit_events.append(ae)

        db.session.commit()
        # make a note of the ids that were given to these events, or rather the order they were generated
        audit_event_id_lookup = {ae.id: i for i, ae in enumerate(audit_events)}
        assert AuditEvent.query.count() == len(service_audit_event_params) + len(supplier_audit_event_params)

        return audit_event_id_lookup


# these actually test a view whose @route is declared in services.py, but the bulk of the implementation is in audits.py
# and it heavily uses BaseTestAuditEvents above
class TestSupplierUpdateAcknowledgement(BaseTestAuditEvents):
    def _assert_nothing_acknowledged(self):
        # check nothing happened to the data
        assert not db.session.query(AuditEvent).filter(db.or_(
            AuditEvent.acknowledged_by.isnot(None),
            AuditEvent.acknowledged_at.isnot(None),
            AuditEvent.acknowledged == db.true(),
        )).all()

    @pytest.mark.parametrize(
        "service_audit_event_params,supplier_audit_event_params,target_audit_event_id,expected_resp_events",
        # where we refer to "id"s in the expected_response_params, because we can't be too sure about the *actual* ids
        # given to objects, we're using 0-based notional "ids" mased on the order the audit events were inserted into
        # the db. service_audit_event_params events are inserted in the order given, followed by the
        # supplier_audit_event_params events. so if we had 5 service_audit_event_params and 2
        # supplier_audit_event_params, "5" would refer to the audit event created by the first-listed
        # supplier_audit_event_params.
        # similarly, where supplier and service "id"s are referred to, the "id"s we're referring to are normalized
        # pseudo-ids from 0-4 inclusive
        chain.from_iterable(
            ((serv_aeps, supp_aeps, tgt_ae_id, expected_resp_events) for tgt_ae_id, expected_resp_events in req_cases)
            for serv_aeps, supp_aeps, req_cases in (
                (
                    (   # service_audit_event_params, as consumed by add_audit_events_by_param_tuples
                        # service pseudo-id, audit type, created_at, acknowledged_at
                        (0, AuditTypes.update_service, datetime(2010, 6, 6), None,),
                        (0, AuditTypes.update_service, datetime(2010, 6, 7), None,),
                        (4, AuditTypes.update_service, datetime(2010, 6, 2), None,),
                    ),
                    (   # supplier_audit_event_params, as consumed by add_audit_events_by_param_tuples
                        # supplier pseudo-id, audit type, created_at, acknowledged_at
                        (0, AuditTypes.supplier_update, datetime(2010, 6, 6), None,),
                    ),
                    (   # and now a series of req_cases - pairs of (tgt_ae_id, expected_resp_events) to test against
                        # the above db scenario. these get flattened out into concrete test scenarios by
                        # chain.from_iterable above before they reach pytest's parametrization
                        (
                            1,
                            frozenset((0, 1,)),
                        ),
                        (
                            2,
                            frozenset((2,)),
                        ),
                        # currently the only exposed route for this view restricts the operation to supplier updates
                        # so we're leaving some cases disabled for now
                        # (
                        #     3,
                        #     frozenset((3,)),
                        # ),
                    ),
                ),
                (
                    (
                        (2, AuditTypes.update_service, datetime(2010, 6, 9), None,),
                        (3, AuditTypes.update_service, datetime(2010, 6, 2), None,),
                        (2, AuditTypes.update_service, datetime(2010, 6, 7), None,),
                        (2, AuditTypes.update_service, datetime(2010, 6, 1), datetime(2010, 6, 1, 1),),
                        (4, AuditTypes.update_service, datetime(2010, 6, 5), None,),
                        (2, AuditTypes.update_service_status, datetime(2010, 6, 2), None,),
                    ),
                    (
                        (0, AuditTypes.supplier_update, datetime(2010, 7, 1), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 7, 9), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 7, 8), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 7, 5), datetime(2010, 8, 1),),
                        (0, AuditTypes.supplier_update, datetime(2010, 7, 9), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 7, 1), datetime(2010, 8, 1),),
                        (1, AuditTypes.supplier_update, datetime(2010, 7, 2), datetime(2010, 8, 1),),
                        (0, AuditTypes.supplier_update, datetime(2010, 7, 6), None,),
                        (0, AuditTypes.supplier_update, datetime(2010, 7, 5), None,),
                    ),
                    (
                        (
                            0,
                            frozenset((0, 2,)),
                        ),
                        (
                            2,
                            frozenset((2,)),
                        ),
                        (
                            4,
                            frozenset((4,)),
                        ),
                        # (
                        #     6,
                        #     frozenset((6,)),
                        # ),
                        # (
                        #     7,
                        #     frozenset((7, 8,)),
                        # ),
                        # (
                        #     10,
                        #     frozenset((6, 10, 13, 14,)),
                        # ),
                        # (
                        #     12,
                        #     frozenset(),  # already acknowledged - should have no effect
                        # ),
                    ),
                ),
                (
                    (
                        (3, AuditTypes.update_service, datetime(2011, 6, 5), None,),
                        (4, AuditTypes.update_service, datetime(2011, 6, 8), None,),
                        (2, AuditTypes.update_service, datetime(2011, 6, 1), None,),
                        # note here deliberate collision of created_at and object_id to verify the secondary-ordering
                        (4, AuditTypes.update_service, datetime(2011, 6, 8), None,),
                        (4, AuditTypes.update_service_status, datetime(2011, 6, 7), datetime(2011, 6, 7, 1),),
                        (4, AuditTypes.update_service, datetime(2011, 6, 6), None,),
                        (4, AuditTypes.update_service, datetime(2011, 6, 2), datetime(2011, 8, 1),),
                    ),
                    (
                        (4, AuditTypes.supplier_update, datetime(2011, 6, 1), None,),
                        (1, AuditTypes.supplier_update, datetime(2011, 6, 9), None,),
                        (1, AuditTypes.supplier_update, datetime(2011, 6, 6), datetime(2011, 8, 1),),
                        # again here
                        (1, AuditTypes.supplier_update, datetime(2011, 6, 9), None,),
                        (3, AuditTypes.supplier_update, datetime(2011, 6, 5), None,),
                        (1, AuditTypes.supplier_update, datetime(2011, 6, 8), None,),
                    ),
                    (
                        (
                            0,
                            frozenset((0,)),
                        ),
                        (
                            1,
                            frozenset((1, 5,)),
                        ),
                        (
                            3,
                            frozenset((1, 3, 5,)),
                        ),
                        # (
                        #     4,
                        #     frozenset(),  # already acknowledged - should have no effect
                        # ),
                        (
                            5,
                            frozenset((5,)),
                        ),
                        (
                            6,
                            frozenset(),  # already acknowledged - should have no effect
                        ),
                        # (
                        #     8,
                        #     frozenset((8, 12,)),
                        # ),
                        # (
                        #     10,
                        #     frozenset((8, 10, 12,)),
                        # ),
                        # (
                        #     11,
                        #     frozenset((11,)),
                        # ),
                        # (
                        #     12,
                        #     frozenset((12,)),
                        # ),
                    ),
                ),
            )
        ),
    )
    def test_acknowledge_including_previous_happy_path(
        self,
        service_audit_event_params,
        supplier_audit_event_params,
        target_audit_event_id,
        expected_resp_events,
    ):
        self.setup_dummy_suppliers(5)
        self.setup_dummy_services(5, supplier_id=1)
        audit_event_id_lookup = self.add_audit_events_by_param_tuples(
            service_audit_event_params,
            supplier_audit_event_params,
        )
        audit_event_id_rlookup = {v: k for k, v in audit_event_id_lookup.items()}
        # because we're doing a fun include-the-servide-id thing on the api endpoint we've got to look it up here,
        # this being the *public* service id
        service_id = db.session.query(Service.service_id).join(
            AuditEvent,
            AuditEvent.object_id == Service.id,
        ).filter(AuditEvent.id == audit_event_id_rlookup[target_audit_event_id]).scalar()

        frozen_time = datetime(2016, 6, 6, 15, 32, 44, 1234)
        with freeze_time(frozen_time):
            response = self.client.post(
                "/services/{}/updates/acknowledge".format(service_id),
                data=json.dumps({
                    'updated_by': "martha.clifford@example.com",
                    "latestAuditEventId": audit_event_id_rlookup[target_audit_event_id],
                }),
                content_type='application/json',
            )

        assert response.status_code == 200
        data = json.loads(response.get_data())

        assert frozenset(audit_event_id_lookup[ae["id"]] for ae in data["auditEvents"]) == expected_resp_events

        assert sorted((
            audit_event_id_lookup[id_],
            acknowledged,
            acknowledged_at,
            acknowledged_by,
        ) for id_, acknowledged, acknowledged_at, acknowledged_by in db.session.query(
            AuditEvent.id,
            AuditEvent.acknowledged,
            AuditEvent.acknowledged_at,
            AuditEvent.acknowledged_by,
        ).all()) == [
            (
                id_,
                (id_ in expected_resp_events) or bool(acknowledged_at),
                (frozen_time if id_ in expected_resp_events else acknowledged_at),
                (
                    "martha.clifford@example.com"
                    if id_ in expected_resp_events else
                    (acknowledged_at and "c.p.mccoy@example.com")
                )
            ) for id_, (
                obj_id,
                audit_type,
                created_at,
                acknowledged_at,
            ) in enumerate(chain(service_audit_event_params, supplier_audit_event_params))
        ]

    def test_acknowledge_including_previous_nonexistent_event(self):
        # would be unfair to not give them any events to start with
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(3, supplier_id=1)
        audit_event_id_lookup = self.add_audit_events_by_param_tuples(
            ((0, AuditTypes.update_service, datetime(2010, 6, 7), None,),),
            ((2, AuditTypes.supplier_update, datetime(2011, 6, 9), None,),),
        )
        audit_event_id_rlookup = {v: k for k, v in audit_event_id_lookup.items()}
        # because we're doing a fun include-the-servide-id thing on the api endpoint we've got to look it up here,
        # this being the *public* service id
        service_id = db.session.query(Service.service_id).join(
            AuditEvent,
            AuditEvent.object_id == Service.id,
        ).filter(AuditEvent.id == audit_event_id_rlookup[0]).scalar()

        response = self.client.post(
            "/services/{}/updates/acknowledge".format(service_id),
            data=json.dumps({
                'updated_by': "martha.clifford@example.com",
                "latestAuditEventId": 314159,
            }),
            content_type='application/json',
        )

        assert response.status_code == 404
        self._assert_nothing_acknowledged()

    def test_acknowledge_including_previous_obj_mismatch(self):
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(3, supplier_id=1)
        audit_event_id_lookup = self.add_audit_events_by_param_tuples(
            ((0, AuditTypes.update_service, datetime(2010, 6, 7), None,),),
            # note here how i'm applying an update_service audit type to a supplier-bound event so that we can be sure
            # we're testing the object mismatch and not the audit_type mismatch
            ((2, AuditTypes.update_service, datetime(2011, 6, 9), None,),),
        )
        audit_event_id_rlookup = {v: k for k, v in audit_event_id_lookup.items()}
        # because we're doing a fun include-the-servide-id thing on the api endpoint we've got to look it up here,
        # this being the *public* service id
        service_id = db.session.query(Service.service_id).join(
            AuditEvent,
            AuditEvent.object_id == Service.id,
        ).filter(AuditEvent.id == audit_event_id_rlookup[0]).scalar()

        response = self.client.post(
            "/services/{}/updates/acknowledge".format(service_id),
            data=json.dumps({
                'updated_by': "martha.clifford@example.com",
                # now specify the id for the event bound to the *supplier*
                "latestAuditEventId": audit_event_id_rlookup[1],
            }),
            content_type='application/json',
        )

        assert response.status_code == 404
        self._assert_nothing_acknowledged()

    def test_acknowledge_including_previous_obj_type_mismatch(self):
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(3, supplier_id=1)
        audit_event_id_lookup = self.add_audit_events_by_param_tuples(
            ((0, AuditTypes.update_service, datetime(2010, 6, 7), None,),),
            # as before, note here how i'm applying an update_service audit type to a supplier-bound event so that we
            # can be sure we're testing the object mismatch and not the audit_type mismatch
            ((2, AuditTypes.update_service, datetime(2011, 6, 9), None,),),
        )
        audit_event_id_rlookup = {v: k for k, v in audit_event_id_lookup.items()}
        # because we're doing a fun include-the-servide-id thing on the api endpoint we've got to look it up here,
        # this being the *public* service id
        supplier_id = db.session.query(AuditEvent.object_id).filter(
            AuditEvent.id == audit_event_id_rlookup[1]
        ).scalar()

        response = self.client.post(
            "/services/{}/updates/acknowledge".format(supplier_id),
            data=json.dumps({
                'updated_by': "martha.clifford@example.com",
                # now specify the id for the event bound to the *supplier*
                "latestAuditEventId": audit_event_id_rlookup[1],
            }),
            content_type='application/json',
        )

        assert response.status_code == 404
        self._assert_nothing_acknowledged()

    def test_acknowledge_including_previous_audit_type_mismatch(self):
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(3, supplier_id=1)
        audit_event_id_lookup = self.add_audit_events_by_param_tuples(
            ((0, AuditTypes.update_service_status, datetime(2010, 6, 7), None,),),
            ((2, AuditTypes.supplier_update, datetime(2011, 6, 9), None,),),
        )
        audit_event_id_rlookup = {v: k for k, v in audit_event_id_lookup.items()}
        # because we're doing a fun include-the-servide-id thing on the api endpoint we've got to look it up here,
        # this being the *public* service id
        service_id = db.session.query(Service.service_id).join(
            AuditEvent,
            AuditEvent.object_id == Service.id,
        ).filter(AuditEvent.id == audit_event_id_rlookup[0]).scalar()

        response = self.client.post(
            "/services/{}/updates/acknowledge".format(service_id),
            data=json.dumps({
                'updated_by': "martha.clifford@example.com",
                "latestAuditEventId": audit_event_id_rlookup[0],
            }),
            content_type='application/json',
        )

        assert response.status_code == 404
        self._assert_nothing_acknowledged()


class TestAuditEvents(BaseTestAuditEvents):
    @pytest.mark.parametrize(
        "service_audit_event_params,supplier_audit_event_params,req_params,expected_resp_events",
        # where we refer to "id"s in the expected_response_params, because we can't be too sure about the *actual* ids
        # given to objects, we're using 0-based notional "ids" based on the order the audit events were inserted into
        # the db. service_audit_event_params events are inserted in the order given, followed by the
        # supplier_audit_event_params events. so if we had 5 service_audit_event_params and 2
        # supplier_audit_event_params, "5" would refer to the audit event created by the first-listed
        # supplier_audit_event_params.
        # similarly, where supplier and service "id"s are referred to, the "id"s we're referring to are normalized
        # pseudo-ids from 0-4 inclusive
        chain.from_iterable(
            ((serv_aeps, supp_aeps, req_params, expected_resp_events) for req_params, expected_resp_events in req_cases)
            for serv_aeps, supp_aeps, req_cases in (
                (
                    (   # service_audit_event_params, as consumed by add_audit_events_by_param_tuples
                        # service pseudo-id, audit type, created_at, acknowledged_at
                        (0, AuditTypes.update_service, datetime(2010, 6, 6), None,),
                        (0, AuditTypes.update_service, datetime(2010, 6, 7), None,),
                        (4, AuditTypes.update_service, datetime(2010, 6, 2), None,),
                    ),
                    (   # supplier_audit_event_params, as consumed by add_audit_events_by_param_tuples
                        # supplier pseudo-id, audit type, created_at, acknowledged_at
                        (0, AuditTypes.supplier_update, datetime(2010, 6, 6), None,),
                    ),
                    (  # and now a series of req_cases - pairs of (req_params, expected_resp_events) to test against
                       # the above db scenario. these get flattened out into concrete test scenarios by
                       # chain.from_iterable above before they reach pytest's parametrization
                        (
                            {"earliest_for_each_object": "true", "latest_first": "true"},
                            (3, 0, 2,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "latest_first": "false"},
                            (2, 0, 3,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "audit-type": "supplier_update"},
                            (3,),
                        ),
                    ),
                ),
                (
                    (   # service_audit_event_params
                        (0, AuditTypes.update_service, datetime(2011, 6, 6), None,),
                        (0, AuditTypes.update_service_status, datetime(2011, 8, 2), None,),
                        (1, AuditTypes.update_service, datetime(2011, 8, 6, 12), datetime(2011, 9, 2),),
                        (1, AuditTypes.update_service, datetime(2011, 8, 6, 9), datetime(2011, 9, 1),),
                        (0, AuditTypes.update_service, datetime(2010, 8, 4), datetime(2011, 9, 2),),
                        (3, AuditTypes.update_service, datetime(2014, 6, 6), None,),
                    ),
                    (   # supplier_audit_event_params
                        (1, AuditTypes.supplier_update, datetime(2010, 2, 6), None,),
                        (0, AuditTypes.supplier_update, datetime(2010, 6, 6), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 2, 6), None,),
                    ),
                    (   # series of req_cases for the above db scenario
                        (
                            {"earliest_for_each_object": "true"},
                            (6, 7, 4, 3, 5,),
                        ),
                        (  # (all of them have this value for user)
                            {"earliest_for_each_object": "true", "user": "henry.flower@example.com"},
                            (6, 7, 4, 3, 5,),
                        ),
                        (  # (none of them have this value for user)
                            {"earliest_for_each_object": "true", "user": "flower"},
                            (),
                        ),
                        (
                            {"earliest_for_each_object": "true", "acknowledged": "false"},
                            (6, 7, 0, 5,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "acknowledged": "true"},
                            (4, 3,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "object-type": "suppliers"},
                            (6, 7,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "audit-date": "2011-08-06"},
                            (3,),
                        ),
                        (
                            {"earliest_for_each_object": "false", "per_page": "100"},
                            (6, 8, 7, 4, 0, 1, 3, 2, 5,),
                        ),
                        (
                            {"per_page": "100"},
                            (6, 8, 7, 4, 0, 1, 3, 2, 5,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "audit-date": "2010-08-06"},
                            (),
                        ),
                    ),
                ),
                (
                    (   # service_audit_event_params
                        (0, AuditTypes.update_service, datetime(2010, 8, 5), datetime(2011, 8, 2),),
                        (0, AuditTypes.update_service, datetime(2010, 8, 4), datetime(2011, 8, 2),),
                    ),
                    (   # supplier_audit_event_params
                        (0, AuditTypes.supplier_update, datetime(2010, 6, 6), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 2, 1), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 2, 6), None,),
                        (0, AuditTypes.supplier_update, datetime(2010, 2, 7), None,),
                        (3, AuditTypes.supplier_update, datetime(2009, 1, 1), None,),
                        (0, AuditTypes.supplier_update, datetime(2010, 2, 3), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 4, 9), None,),
                        (2, AuditTypes.supplier_update, datetime(2010, 1, 1), None,),
                        (1, AuditTypes.supplier_update, datetime(2010, 8, 8), None,),
                    ),
                    (   # series of req_cases for the above db scenario
                        (
                            {"earliest_for_each_object": "true", "latest_first": "true", "per_page": "4"},
                            (1, 7, 3, 9,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "object-type": "suppliers", "latest_first": "false"},
                            (6, 9, 3, 7,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "per_page": "3", "page": "2"},
                            (7, 1,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "object-type": "suppliers", "acknowledged": "true"},
                            (),
                        ),
                    ),
                ),
                (
                    (   # service_audit_event_params
                    ),
                    (   # supplier_audit_event_params
                        (0, AuditTypes.supplier_update, datetime(2015, 3, 2), None,),
                        (3, AuditTypes.supplier_update, datetime(2015, 8, 8), None,),
                        (4, AuditTypes.supplier_update, datetime(2015, 4, 6), None,),
                        (2, AuditTypes.supplier_update, datetime(2015, 3, 3), None,),
                        (1, AuditTypes.supplier_update, datetime(2005, 8, 9), None,),
                        (1, AuditTypes.supplier_update, datetime(2015, 2, 4), None,),
                        (2, AuditTypes.supplier_update, datetime(2015, 1, 1), None,),
                        (4, AuditTypes.supplier_update, datetime(2015, 9, 3), None,),
                        (1, AuditTypes.supplier_update, datetime(2015, 4, 6), None,),
                        (1, AuditTypes.supplier_update, datetime(2015, 4, 6), None,),
                    ),
                    (   # series of req_cases for the above db scenario
                        (
                            {"earliest_for_each_object": "true", "acknowledged": "false"},
                            (4, 6, 0, 2, 1,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "audit-date": "2015-04-06"},
                            (2, 8,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "latest_first": "true", "per_page": "100"},
                            (1, 2, 0, 6, 4,),
                        ),
                        (
                            {"earliest_for_each_object": "true", "acknowledged": "true"},
                            (),
                        ),
                    ),
                ),
            )
        ),
    )
    def test_earliest_for_each_object(
        self,
        service_audit_event_params,
        supplier_audit_event_params,
        req_params,
        expected_resp_events,
    ):
        self.setup_dummy_suppliers(5)
        self.setup_dummy_services(5, supplier_id=1)
        audit_event_id_lookup = self.add_audit_events_by_param_tuples(
            service_audit_event_params,
            supplier_audit_event_params,
        )

        response = self.client.get('/audit-events?{}'.format(urlencode(req_params)))

        assert response.status_code == 200
        data = json.loads(response.get_data())

        assert tuple(audit_event_id_lookup[ae["id"]] for ae in data["auditEvents"]) == expected_resp_events

    def test_only_one_audit_event_created(self):
        count = AuditEvent.query.count()
        self.add_audit_event()
        assert AuditEvent.query.count() == count + 1

    def test_should_get_audit_event(self):
        supplier_id = self.setup_dummy_suppliers(1)[0]
        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id).first()
        object_id = supplier.id
        aid = self.add_audit_event(0, db_object=supplier)

        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())
        assert response.status_code == 200
        expected = {
            'links': {'self': mock.ANY},
            'type': 'supplier_update',
            'acknowledged': False,
            'user': '0',
            'data': {'request': 'data'},
            'objectType': 'Supplier',
            'objectId': object_id,
            'id': aid,
            'createdAt': mock.ANY
        }
        assert expected in data['auditEvents']

    def test_should_get_audit_events_sorted(self):
        self.add_audit_events(5)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert data['auditEvents'][0]['user'] == '0'
        assert data['auditEvents'][4]['user'] == '4'

        response = self.client.get('/audit-events?latest_first=true')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert data['auditEvents'][0]['user'] == '4'
        assert data['auditEvents'][4]['user'] == '0'

    def test_should_get_audit_event_using_audit_date(self):
        today = datetime.utcnow().strftime("%Y-%m-%d")

        self.add_audit_event()
        response = self.client.get('/audit-events?audit-date={}'.format(today))
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 1
        assert data['auditEvents'][0]['user'] == '0'
        assert data['auditEvents'][0]['data']['request'] == 'data'

    def test_should_not_get_audit_event_for_date_with_no_events(self):
        self.add_audit_event()
        response = self.client.get('/audit-events?audit-date=2000-01-01')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 0

    @pytest.mark.parametrize(
        ("date_range_query", "number_of_events"),
        (
            ("<=2000-12-31", 4),
            (">=2000-01-01", 4),
            ("<2000-12-31", 3),
            (">2000-01-01", 3),
            ("2000-01-02..2000-12-30", 2),
        ))
    def test_can_find_audit_events_in_date_range(self, date_range_query, number_of_events):
        AuditEvent.query.delete()

        self.add_audit_event(created_at=datetime(2000, 1, 1))
        self.add_audit_event(created_at=datetime(2000, 1, 2))
        self.add_audit_event(created_at=datetime(2000, 2, 5))
        self.add_audit_event(created_at=datetime(2000, 12, 31))

        response = self.client.get(
            "/audit-events",
            query_string={"audit-date": date_range_query},
        )
        assert response.status_code == 200
        events = response.json["auditEvents"]
        assert len(events) == number_of_events

    @pytest.mark.parametrize(
        "invalid_date_string",
        (
            "invalid",
            ">=",
            "<invalid",
            "3000-30-30",
        ))
    def test_should_reject_invalid_audit_dates(self, invalid_date_string):
        self.add_audit_event()
        response = self.client.get(
            "/audit-events",
            query_string={"audit-date": invalid_date_string}
        )

        assert response.status_code == 400

    def test_should_get_audit_event_by_type(self):
        self.add_audit_event(type=AuditTypes.contact_update)
        self.add_audit_event(type=AuditTypes.supplier_update)
        response = self.client.get('/audit-events?audit-type=contact_update')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 1
        assert data['auditEvents'][0]['user'] == '0'
        assert data['auditEvents'][0]['type'] == 'contact_update'
        assert data['auditEvents'][0]['data']['request'] == 'data'

    def test_should_reject_invalid_audit_type(self):
        self.add_audit_event()
        response = self.client.get('/audit-events?audit-type=invalid')

        assert response.status_code == 400

    def test_should_get_audit_event_by_object(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=suppliers&object-id=1')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 1
        assert data['auditEvents'][0]['user'] == 'rob'

    def test_should_get_audit_events_by_object_type(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=suppliers')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data["auditEvents"]) == 3

    def test_get_audit_event_for_missing_object_returns_404(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=suppliers&object-id=100000')

        assert response.status_code == 404

    def test_should_only_get_audit_event_with_correct_object_type(self):
        self.add_audit_events_with_db_object()

        # Create a second AuditEvent with the same object_id but with a
        # different object_type to check that we're not filtering based
        # on object_id only
        supplier = Supplier.query.filter(Supplier.supplier_id == 1).first()
        event = AuditEvent(
            audit_type=AuditTypes.supplier_update,
            db_object=supplier,
            user='not rob',
            data={'request': "data"}
        )
        event.object_type = 'Service'

        db.session.add(event)
        db.session.commit()

        response = self.client.get('/audit-events?object-type=suppliers&object-id=1')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 1
        assert data['auditEvents'][0]['user'] == 'rob'

    @pytest.mark.parametrize("qstr,n_expected_results", (
        ("user=rod", 1),
        ("user=rob", 3),
        ("user=", 4),
        ("user=ro", 0),  # asserting that this isn't a substring search
    ))
    def test_should_only_get_audit_event_with_correct_user(self, qstr, n_expected_results):
        self.add_audit_events_with_db_object()

        # create AuditEvent with different user value
        supplier = Supplier.query.filter(Supplier.supplier_id == 1).first()
        event = AuditEvent(
            audit_type=AuditTypes.supplier_update,
            db_object=supplier,
            user='rod',
            data={'request': "data"}
        )
        event.object_type = 'Supplier'

        db.session.add(event)
        db.session.commit()

        response = self.client.get('/audit-events?{}'.format(qstr))
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == n_expected_results

    def test_should_reject_invalid_object_type(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=invalid&object-id=1')

        assert response.status_code == 400

    def test_should_reject_object_id_if_no_object_type_is_given(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-id=1')

        assert response.status_code == 400

    def test_should_get_audit_events_ordered_by_created_date(self):
        self.add_audit_events(5)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 5

        assert data['auditEvents'][4]['user'] == '4'
        assert data['auditEvents'][3]['user'] == '3'
        assert data['auditEvents'][2]['user'] == '2'
        assert data['auditEvents'][1]['user'] == '1'
        assert data['auditEvents'][0]['user'] == '0'

    def test_should_reject_invalid_page(self):
        self.add_audit_event()
        response = self.client.get('/audit-events?page=invalid')

        assert response.status_code == 400

    def test_should_reject_missing_page(self):
        self.add_audit_event()
        response = self.client.get('/audit-events?page=')

        assert response.status_code == 400

    def test_should_return_404_if_page_exceeds_results(self):
        self.add_audit_events(7)
        response = self.client.get('/audit-events?page=100')

        assert response.status_code == 404

    def test_should_get_audit_events_paginated(self):
        self.add_audit_events(7)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 5
        next_link = data['links']['next']
        assert 'page=2' in next_link
        assert data['auditEvents'][0]['user'] == '0'
        assert data['auditEvents'][1]['user'] == '1'
        assert data['auditEvents'][2]['user'] == '2'
        assert data['auditEvents'][3]['user'] == '3'
        assert data['auditEvents'][4]['user'] == '4'

    def test_paginated_audit_events_page_two(self):
        self.add_audit_events(7)

        response = self.client.get('/audit-events?page=2')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 2
        prev_link = data['links']['prev']
        assert 'page=1' in prev_link
        assert 'next' not in data['links']
        assert data['auditEvents'][0]['user'] == '5'
        assert data['auditEvents'][1]['user'] == '6'

    def test_paginated_audit_with_custom_page_size(self):
        self.add_audit_events(12)
        response = self.client.get('/audit-events?per_page=10')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 10

    def test_paginated_audit_with_custom_page_size_and_specified_page(self):
        self.add_audit_events(12)
        response = self.client.get('/audit-events?page=2&per_page=10')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['auditEvents']) == 2
        prev_link = data['links']['prev']
        assert 'page=1' in prev_link
        assert 'next' not in data['links']

    def test_paginated_audit_with_invalid_custom_page_size(self):
        self.add_audit_event()
        response = self.client.get('/audit-events?per_page=foo')
        assert response.status_code == 400

    @pytest.mark.parametrize("search_term", ("3", "03",))  # test search term is normalized as integer
    def test_should_get_audit_events_by_draft_id_field_in_data(self, search_term):
        for id_, info in [(0, 'miss'), (3, 'hit'), (2, 'miss'), (7, 'miss'), (3, 'hit'), (1, 'miss')]:
            self.add_audit_event(data={'draftId': id_, 'info': info})

        response = self.client.get(f'/audit-events?data-draft-service-id={search_term}')
        audit_events = json.loads(response.get_data())['auditEvents']

        assert response.status_code == 200
        assert len(audit_events) == 2
        assert all(audit_event['data']['draftId'] == 3 for audit_event in audit_events)
        assert all(audit_event['data']['info'] == 'hit' for audit_event in audit_events)

    @pytest.mark.parametrize("search_term", ("3", "03",))  # test search term is normalized as integer
    def test_should_get_audit_events_by_supplier_id_field_in_data(self, search_term):
        for id_, info in [(0, 'miss'), (3, 'hit'), (2, 'miss'), (7, 'miss'), (3, 'hit'), (1, 'miss')]:
            self.add_audit_event(data={'supplierId': id_, 'info': info})

        response = self.client.get(f'/audit-events?data-supplier-id={search_term}')
        audit_events = json.loads(response.get_data())['auditEvents']

        assert response.status_code == 200
        assert len(audit_events) == 2
        assert all(audit_event['data']['supplierId'] == 3 for audit_event in audit_events)
        assert all(audit_event['data']['info'] == 'hit' for audit_event in audit_events)

    @pytest.mark.parametrize("search_term", ("3", "03",))  # test search term is normalized as integer
    def test_should_not_care_if_supplier_id_field_is_int_or_string(self, search_term):
        for id_, info in [(0, 'miss'), ('3', 'hit'), (2, 'miss'), (7, 'miss'), (3, 'hit'), (1, 'miss')]:
            self.add_audit_event(data={'supplierId': id_, 'info': info})

        response = self.client.get(f'/audit-events?data-supplier-id={search_term}')
        audit_events = json.loads(response.get_data())['auditEvents']

        assert response.status_code == 200
        assert len(audit_events) == 2
        assert {audit_event['data']['supplierId'] for audit_event in audit_events} == {3, '3'}
        assert all(audit_event['data']['info'] == 'hit' for audit_event in audit_events)

    def test_should_not_choke_if_supplier_id_field_in_data_does_not_exist(self):
        for id_, info in [(0, 'miss'), (3, 'hit'), (2, 'miss'), (7, 'miss'), (3, 'hit'), (1, 'miss')]:
            self.add_audit_event(data={'supplierId': id_, 'info': info})
        self.add_audit_event(data={'something': 'completely different'})

        response = self.client.get('/audit-events?data-supplier-id=3')
        audit_events = json.loads(response.get_data())['auditEvents']

        assert response.status_code == 200
        assert len(audit_events) == 2
        assert all(audit_event['data']['supplierId'] == 3 for audit_event in audit_events)
        assert all(audit_event['data']['info'] == 'hit' for audit_event in audit_events)

    def test_should_search_for_deprecated_supplier_id_field_key(self):
        for id_, info in [(0, 'miss'), (3, 'hit'), (2, 'miss'), (7, 'miss'), (4, 'hit'), (1, 'miss')]:
            self.add_audit_event(data={'supplierId': id_, 'info': info})
        self.add_audit_event(data={'supplier_id': 3, 'info': 'hit'})

        response = self.client.get('/audit-events?data-supplier-id=3')
        audit_events = json.loads(response.get_data())['auditEvents']

        assert response.status_code == 200
        assert len(audit_events) == 2
        assert any(audit_event['data'].get('supplierId') == 3 for audit_event in audit_events)
        assert any(audit_event['data'].get('supplier_id') == 3 for audit_event in audit_events)
        assert all(audit_event['data']['info'] == 'hit' for audit_event in audit_events)

    def test_reject_invalid_audit_id_on_acknowledgement(self):
        res = self.client.post(
            '/audit-events/invalid-id!/acknowledge',
            data=json.dumps({'key': 'value'}),
            content_type='application/json')

        assert res.status_code == 404

    def test_reject_if_no_updater_details_on_acknowledgement(self):
        res = self.client.post(
            '/audit-events/123/acknowledge',
            data={},
            content_type='application/json')

        assert res.status_code == 400

    def test_should_update_audit_event(self):
        self.add_audit_event()
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get('/audit-events')
        new_data = json.loads(new_response.get_data())
        assert res.status_code == 200
        assert new_data['auditEvents'][0]['acknowledged'] is True
        assert new_data['auditEvents'][0]['acknowledgedBy'] == 'tests'

    def test_should_get_all_audit_events(self):
        self.add_audit_events(2)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get('/audit-events')
        new_data = json.loads(new_response.get_data())
        assert res.status_code == 200
        assert len(new_data['auditEvents']) == 2

        # all should return both
        new_response = self.client.get('/audit-events?acknowledged=all')
        new_data = json.loads(new_response.get_data())
        assert res.status_code == 200
        assert len(new_data['auditEvents']) == 2

    def test_should_get_only_acknowledged_audit_events(self):
        self.add_audit_events(2)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get(
            '/audit-events?acknowledged=true'
        )
        new_data = json.loads(new_response.get_data())
        assert res.status_code == 200
        assert len(new_data['auditEvents']) == 1
        assert new_data['auditEvents'][0]['id'] == data['auditEvents'][0]['id']

    def test_should_get_only_not_acknowledged_audit_events(self):
        self.add_audit_events(2)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get(
            '/audit-events?acknowledged=false'
        )
        new_data = json.loads(new_response.get_data())
        assert res.status_code == 200
        assert len(new_data['auditEvents']) == 1
        assert new_data['auditEvents'][0]['id'] == data['auditEvents'][1]['id']

    def test_audit_event_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        audit_event_id = self.add_audit_event(type=AuditTypes.update_service)
        audit_event = AuditEvent.query.get(audit_event_id)
        assert sorted(audit_event.serialize().keys()) == sorted(AuditEventStub().response().keys())


class TestCreateAuditEvent(BaseApplicationTest, FixtureMixin):
    @staticmethod
    def audit_event():
        audit_event = {
            "type": "register_framework_interest",
            "user": "A User",
            "data": {
                "Key": "value"
            },
        }

        return audit_event

    def audit_event_with_db_object(self):
        audit_event = self.audit_event()
        self.setup_dummy_suppliers(1)
        audit_event['objectType'] = 'suppliers'
        audit_event['objectId'] = 0

        return audit_event

    def test_create_an_audit_event(self):
        audit_event = self.audit_event()

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')

        assert res.status_code == 201

    def test_create_an_audit_event_with_an_associated_object(self):
        audit_event = self.audit_event_with_db_object()

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')

        assert res.status_code == 201

    def test_create_audit_event_with_no_user(self):
        audit_event = self.audit_event()
        del audit_event['user']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')

        assert res.status_code == 201

    def test_should_fail_if_no_type_is_given(self):
        audit_event = self.audit_event()
        del audit_event['type']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'].startswith("Invalid JSON")

    def test_should_fail_if_an_invalid_type_is_given(self):
        audit_event = self.audit_event()
        audit_event['type'] = 'invalid'

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'] == "invalid audit type supplied"

    def test_should_fail_if_no_data_is_given(self):
        audit_event = self.audit_event()
        del audit_event['data']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'].startswith("Invalid JSON")

    def test_should_fail_if_invalid_objectType_is_given(self):
        audit_event = self.audit_event_with_db_object()
        audit_event['objectType'] = 'invalid'

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'] == "invalid object type supplied"

    def test_should_fail_if_objectType_but_no_objectId_is_given(self):
        audit_event = self.audit_event_with_db_object()
        del audit_event['objectId']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'] == "object type cannot be provided without an object ID"

    def test_should_fail_if_objectId_but_no_objectType_is_given(self):
        audit_event = self.audit_event_with_db_object()
        del audit_event['objectType']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'] == "object ID cannot be provided without an object type"

    def test_should_fail_if_db_object_does_not_exist(self):
        audit_event = self.audit_event_with_db_object()
        audit_event['objectId'] = 6

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert data['error'] == "referenced object does not exist"


class TestGetAuditEvent(BaseTestAuditEvents):
    def test_get_existing_audit_event(self):
        event_ids = self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events/{}'.format(event_ids[0]))

        assert response.status_code == 200
        data = json.loads(response.get_data())

        assert data["auditEvents"]["id"] == event_ids[0]
        assert data["auditEvents"]["type"] == "contact_update"
        assert data["auditEvents"]["user"] == "rob"

    def test_get_nonexisting_audit_event(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events/314159')

        assert response.status_code == 404
