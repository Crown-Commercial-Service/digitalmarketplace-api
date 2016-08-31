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

    def test_it_gets_a_framework_agreement_by_id(self, supplier_framework):
        example_time = datetime(2016, 10, 1, 1, 1, 1)
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=example_time,
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path'
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id'],
            'signedAgreementReturnedAt': example_time.isoformat(),
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
        }
