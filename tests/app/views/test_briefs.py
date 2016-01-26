from ..helpers import BaseApplicationTest

from app import db


class TestBriefs(BaseApplicationTest):
    def setup(self):
        super(TestBriefs, self).setup()
        self.setup_dummy_user()
        with self.app.app_context():
            db.session.commit()

    def test_create_brief_with_no_data(self):
        res = self.client.post('/briefs')

        assert res.status_code == 400
