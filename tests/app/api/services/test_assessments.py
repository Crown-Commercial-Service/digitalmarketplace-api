import pytest

from app.api.services import assessments
from app.models import Assessment, Domain, Supplier, SupplierDomain, db
from tests.app.helpers import BaseApplicationTest


class TestAssessmentsService(BaseApplicationTest):
    def setup(self):
        super(TestAssessmentsService, self).setup()

    @pytest.fixture()
    def domain_assessments(self, app):
        with app.app_context():
            db.session.add(Assessment(id=1, supplier_domain_id=1, active=True))
            db.session.add(Assessment(id=2, supplier_domain_id=2, active=True))
            db.session.add(Assessment(id=3, supplier_domain_id=3, active=False))
            db.session.add(Assessment(id=4, supplier_domain_id=4, active=True))
            db.session.add(Assessment(id=5, supplier_domain_id=5, active=True))
            db.session.add(Assessment(id=6, supplier_domain_id=6, active=True))
            db.session.add(Assessment(id=7, supplier_domain_id=7, active=True))
            yield db.session.query(Assessment).all()

    @pytest.fixture()
    def domains(self, app):
        with app.app_context():
            yield db.session.query(Domain).all()

    @pytest.fixture()
    def suppliers(self, app):
        with app.app_context():
            db.session.add(Supplier(id=1, code=1, name='Seller 1'))
            db.session.add(Supplier(id=2, code=2, name='Seller 2'))
            yield db.session.query(Supplier).all()

    @pytest.fixture()
    def supplier_domains(self, app):
        with app.app_context():
            db.session.add(SupplierDomain(id=1, supplier_id=1, domain_id=11, status='unassessed'))
            db.session.add(SupplierDomain(id=2, supplier_id=1, domain_id=8, status='unassessed'))
            db.session.add(SupplierDomain(id=3, supplier_id=1, domain_id=6, status='unassessed'))
            db.session.add(SupplierDomain(id=4, supplier_id=1, domain_id=1, status='rejected'))
            db.session.add(SupplierDomain(id=5, supplier_id=2, domain_id=11, status='assessed'))
            db.session.add(SupplierDomain(id=6, supplier_id=2, domain_id=8, status='rejected'))
            db.session.add(SupplierDomain(id=7, supplier_id=2, domain_id=1, status='unassessed'))
            yield db.session.query(SupplierDomain).all()

    def test_active_unassessed_assessments_are_returned(self, domains, suppliers, supplier_domains, domain_assessments):
        open_assessments = assessments.get_open_assessments()
        assert len(open_assessments) == 2
        assert open_assessments[0]['supplier_code'] == 1
        assert 'Data science' in open_assessments[0]['domains']
        assert 'Cyber security' in open_assessments[0]['domains']
        assert open_assessments[1]['supplier_code'] == 2
        assert 'Strategy and Policy' in open_assessments[1]['domains']
