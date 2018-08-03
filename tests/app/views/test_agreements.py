import json
import mock
import datetime

from tests.app.helpers import BaseApplicationTest
from app.models import db, SignedAgreement, Agreement


class TestAgreements(BaseApplicationTest):
    def list_agreements(self, **parameters):
        return self.client.get('/agreements', query_string=parameters)

    def list_signed_agreements(self, supplier_code, **parameters):
        return self.client.get('/agreements/signed/{}'.format(supplier_code), query_string=parameters)

    def sign_agreement(self, data):
        return self.client.post(
            '/agreements/signed',
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'},
                'signed_agreement': data,
            }),
            content_type='application/json'
        )

    def setup(self):
        super(TestAgreements, self).setup()

        with self.app.app_context():
            self.setup_dummy_suppliers(2)
            self.setup_dummy_user(id=0, role="supplier", supplier_code=0)
            self.setup_dummy_user(id=1, role="supplier", supplier_code=1)
            agreement = Agreement(
                version='1.0',
                url='http://url',
                is_current=False
            )
            db.session.add(agreement)
            new_agreement = Agreement(
                version='2.0',
                url='http://url',
                is_current=True
            )
            db.session.add(new_agreement)
            db.session.flush()
            signed_agreement = SignedAgreement(agreement_id=agreement.id, supplier_code=0, user_id=0,
                                               signed_at=datetime.datetime.now())
            db.session.add(signed_agreement)
            signed_new_agreement = SignedAgreement(agreement_id=new_agreement.id, supplier_code=1, user_id=0,
                                                   signed_at=datetime.datetime.now())
            db.session.add(signed_new_agreement)
            db.session.commit()

    def test_sign_agreement(self):
        with self.app.app_context():
            agreements = json.loads(self.list_agreements().get_data(as_text=True))
            res = self.sign_agreement(
                {
                    'agreement_id': str(agreements['agreements'][0]['id']),
                    'user_id': 0,
                    'supplier_code': 0
                }
            )

            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 201, data

    def test_sign_agreement_unauthorised(self):
        with self.app.app_context():
            agreements = json.loads(self.list_agreements().get_data(as_text=True))
            res = self.sign_agreement(
                {
                    'agreement_id': str(agreements['agreements'][0]['id']),
                    'user_id': 0,
                    'supplier_code': 1
                }
            )

            assert res.status_code == 400

    def test_list_agreements(self):
        with self.app.app_context():
            res = self.list_agreements()
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['agreements']) == 2
            assert 'self' in data['links']

    def test_list_current_agreements(self):
        with self.app.app_context():
            res = self.list_agreements(current_only=True)
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['agreements']) == 1
            assert 'self' in data['links']

    def test_list_signed_agreements(self):
        with self.app.app_context():
            res = self.list_signed_agreements(0)
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['agreements']) == 1
            assert 'self' in data['links']

            res = self.list_signed_agreements(2, current_only=True)
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['agreements']) == 0
            assert 'self' in data['links']

            res = self.list_signed_agreements(1, current_only=True)
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['agreements']) == 1
            assert 'self' in data['links']

            res = self.list_signed_agreements(3)
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['agreements']) == 0
            assert 'self' in data['links']
