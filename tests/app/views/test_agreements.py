import json
import pytest
from datetime import datetime
from app.models import FrameworkAgreement, db
from ..helpers import BaseApplicationTest


class TestGetFrameworkAgreement(BaseApplicationTest):

    def create_agreement(self, supplier_framework, **framework_agreement_kwargs):
        with self.app.app_context():
            agreement = FrameworkAgreement(
                supplier_id=supplier_framework['supplier_id'],
                framework_id=supplier_framework['framework_id'],
                **framework_agreement_kwargs)
            db.session.add(agreement)
            db.session.commit()

            return agreement.id

    def test_it_gets_a_newly_created_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id']
        }

    def test_it_returns_a_framework_agreement_with_details_only(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'details': 'here'}
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id'],
            'signedAgreementDetails': {'details': 'here'},
        }

    def test_it_gets_a_signed_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path'
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id'],
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
        }

    def test_it_gets_a_countersigned_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            countersigned_agreement_details={'countersigneddetails': 'here'},
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1)
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id'],
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementDetails': {'countersigneddetails': 'here'},
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
        }

    def test_it_gets_a_countersigned_and_uploaded_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            countersigned_agreement_details={'countersigneddetails': 'here'},
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1),
            countersigned_agreement_path='/example.pdf'
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id'],
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementDetails': {'countersigneddetails': 'here'},
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
            'countersignedAgreementPath': '/example.pdf'
        }
