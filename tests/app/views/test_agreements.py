import json
import pytest
from app.models import FrameworkAgreement, db
from ..helpers import BaseApplicationTest


class TestGetFrameworkAgreement(BaseApplicationTest):

    def create_agreement(self, supplier_framework):
        with self.app.app_context():
            agreement = FrameworkAgreement(
                supplier_id=supplier_framework['supplier_id'],
                framework_id=supplier_framework['framework_id'])
            db.session.add(agreement)
            db.session.commit()

            return agreement.id

    def test_it_gets_a_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplier_id'],
            'frameworkId': supplier_framework['framework_id'],
        }
