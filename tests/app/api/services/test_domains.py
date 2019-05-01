import pytest

from app.api.services import domain_service
from app.models import Domain, db
from tests.app.helpers import BaseApplicationTest


class TestDomainsService(BaseApplicationTest):
    def setup(self):
        super(TestDomainsService, self).setup()

    @pytest.fixture()
    def domains(self, app):
        with app.app_context():
            yield db.session.query(Domain).all()

    def test_change_training_transformation_not_returned_as_active_domain(self, domains):
        active_domains = domain_service.get_active_domains()
        active_domain_names = [domain.name for domain in active_domains]
        assert 'Change, Training and Transformation' not in active_domain_names
