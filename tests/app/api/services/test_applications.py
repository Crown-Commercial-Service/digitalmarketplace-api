import pytest

from app.api.services import application_service
from app.models import Application, db
from tests.app.helpers import BaseApplicationTest


class TestApplicationService(BaseApplicationTest):
    def setup(self):
        super(TestApplicationService, self).setup()

    @pytest.fixture()
    def applications(self, app):
        with app.app_context():
            db.session.add(Application(id=1, data={}, status='submitted'))
            db.session.add(Application(id=2, data={}, status='saved'))
            db.session.add(Application(id=3, data={}, status='approved'))
            db.session.add(Application(id=4, data={}, status='submitted'))
            db.session.commit()
            yield db.session.query(Application).all()

    def test_get_submitted_application_ids(self, applications):
        submitted_applications = application_service.get_submitted_application_ids()
        assert submitted_applications == [1, 4]
