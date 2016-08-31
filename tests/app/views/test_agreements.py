import json
import pytest
from app.models import SupplierFramework, FrameworkAgreement, db
from ..helpers import BaseApplicationTest

class TestFrameworkAgreements(BaseApplicationTest):

    def setup(self):
        super(TestFrameworkAgreements, self).setup()
        with self.app.app_context():
            self.setup_dummy_suppliers(1)

            supplier_framework = SupplierFramework(supplier_id=0, framework_id=1)
            db.session.add(supplier_framework)

            framework_agreement = FrameworkAgreement(supplier_id=0, framework_id=1)
            db.session.add(framework_agreement)
            db.session.commit()

            self.agreement_id = framework_agreement.id



    def test_it_gets_a_framework_agreement_by_id(self):
        framework_agreement = FrameworkAgreement(supplier_id=0, framework_id=1)
        res = self.client.get('/agreements/{}'.format(self.agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': self.agreement_id,
            'supplierId': 0,
            'frameworkId': 1,
        }
