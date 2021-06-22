

from app.models import Supplier, DraftService, Domain

from .helpers import BaseApplicationTest, assert_api_compatible

from flask import current_app
from app import db

from app.modelsbase import get_properties
import json
import pendulum


class TestModelbase(BaseApplicationTest):
    def test_repr(self):
        ds = DraftService()
        assert repr(ds) == '<DraftService: id=None, service_id=None, supplier_code=None, lot=None>'
        s = Supplier()
        assert repr(s) == '<Supplier: id=None, name=None>'

    def test_supplier_json(self):
        with pendulum.test(pendulum.now('UTC')):
            with self.app.test_request_context('/hello'):
                self.setup_dummy_suppliers(1)
                s = Supplier.query.first()

                assert 'brief_responses' not in s.serializable
                assert set(s._relationships + s._fields) == set(s._props)

                s.creation_time = s.creation_time.in_tz('utc')
                s.last_update_time = s.last_update_time.in_tz('utc')

                # testing a round trip update of fields
                before_update = json.loads(s.json)
                for_update = before_update.copy()
                for_update['new_key'] = 'new_value'

                # don't test domains round trip as legacy values are round trip only
                del for_update['address']
                del for_update['domains']

                s.update_from_json(for_update)

                db.session.flush()
                after_update = json.loads(s.json)

                assert_api_compatible(
                    before_update,
                    after_update
                )

                assert after_update['new_key'] == 'new_value'
