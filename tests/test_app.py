from app import db
from app.models import Service

from .helpers import BaseApplicationTest


class TestApplication(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/')
        assert 200 == response.status_code
        assert u'Hello You Dogs' in response.data.decode('utf8')

    def test_404(self):
        response = self.client.get('/not-found')
        assert 404 == response.status_code

    def test_bearer_token_is_required(self):
        self.do_not_provide_access_token()
        response = self.client.get('/')
        assert 401 == response.status_code
        assert 'WWW-Authenticate' in response.headers

    def test_invalid_bearer_token_is_required(self):
        self.do_not_provide_access_token()
        response = self.client.get(
            '/',
            headers={'Authorization': 'Bearer invalid-token'})
        assert 403 == response.status_code

    def test_get_non_existent_service(self):
        response = self.client.get('/services/1')
        assert 404 == response.status_code

    def test_get_service(self):
        with self.app.app_context():
            db.session.add(Service(data={'foo': 'bar'}))
        response = self.client.get('/services/1')
        assert 200 == response.status_code
