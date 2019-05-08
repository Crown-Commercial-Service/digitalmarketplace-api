import pytest

from app.api.services import supplier_domain_service
from app.models import Supplier, Domain, SupplierDomain, Assessment, db
from tests.app.helpers import BaseApplicationTest


class TestSupplierDomainsService(BaseApplicationTest):
    def setup(self):
        super(TestSupplierDomainsService, self).setup()

    @pytest.fixture()
    def supplier(self, app):
        with app.app_context():
            db.session.add(
                Supplier(
                    id=100,
                    code=100,
                    name='Test Supplier',
                    website='http://www.dta.gov.au',
                    abn='1234567890',
                    data={},
                    status='complete'
                )
            )
            db.session.add(
                Supplier(
                    id=101,
                    code=101,
                    name='Test Supplier 1',
                    website='http://www.dta1.gov.au',
                    abn='1234567891',
                    data={},
                    status='complete'
                )
            )
            db.session.commit()
            yield db.session.query(Supplier).all()

    @pytest.fixture()
    def assessment(self, app):
        with app.app_context():
            db.session.add(
                Assessment(
                    id=100,
                    supplier_domain_id=100,
                    active=True
                )
            )
            db.session.add(
                Assessment(
                    id=101,
                    supplier_domain_id=101,
                    active=False
                )
            )
            db.session.commit()
            yield db.session.query(Assessment).all()

    @pytest.fixture()
    def supplier_domains(self, app):
        with app.app_context():
            db.session.add(
                SupplierDomain(
                    id=100,
                    supplier_id=100,
                    domain_id=1,
                    status='assessed',
                    price_status='approved'
                )
            )
            db.session.add(
                SupplierDomain(
                    id=101,
                    supplier_id=100,
                    domain_id=2,
                    status='unassessed',
                    price_status='unassessed'
                )
            )
            db.session.add(
                SupplierDomain(
                    id=102,
                    supplier_id=100,
                    domain_id=3,
                    status='unassessed',
                    price_status='unassessed'
                )
            )
            yield db.session.query(SupplierDomain).all()

    def test_get_supplier_domains(self, supplier, supplier_domains, assessment):
        submitted_applications = supplier_domain_service.get_supplier_domains(100)
        assert len(submitted_applications) == 3
        for submitted_application in submitted_applications:
            if submitted_application.get('service_id') == 1:
                assert submitted_application.get('id') == 100
                assert submitted_application.get('status') == 'assessed'
                assert submitted_application.get('active_assessment') is True
            if submitted_application.get('service_id') == 3:
                assert submitted_application.get('id') == 102
                assert submitted_application.get('status') == 'unassessed'
                assert submitted_application.get('active_assessment') is None
