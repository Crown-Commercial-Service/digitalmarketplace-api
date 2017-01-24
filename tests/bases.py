from nose.tools import assert_equal, assert_in

from app import create_app, db
from app.models import Framework, FrameworkLot


class WSGIApplicationWithEnvironment(object):
    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs

    def __call__(self, environ, start_response):
        for key, value in self.kwargs.items():
            environ[key] = value
        return self.app(environ, start_response)


class BaseApplicationTest(object):
    lots = {
        "iaas": "G6-IaaS.json",
        "saas": "G6-SaaS.json",
        "paas": "G6-PaaS.json",
        "scs": "G6-SCS.json"
    }

    config = None

    def setup(self):
        self.app = create_app('test')
        self.client = self.app.test_client()
        self.setup_authorization(self.app)

    def setup_authorization(self, app):
        """Set up bearer token and pass on all requests"""
        valid_token = 'valid-token'
        app.wsgi_app = WSGIApplicationWithEnvironment(
            app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(valid_token))
        self._auth_tokens = app.config['DM_API_AUTH_TOKENS']
        app.config['DM_API_AUTH_TOKENS'] = valid_token

    def do_not_provide_access_token(self):
        self.app.wsgi_app = self.app.wsgi_app.app

    def teardown(self):
        self.teardown_authorization()
        self.teardown_database()

    def teardown_authorization(self):
        if self._auth_tokens is None:
            del self.app.config['DM_API_AUTH_TOKENS']
        else:
            self.app.config['DM_API_AUTH_TOKENS'] = self._auth_tokens

    def teardown_database(self):
        with self.app.app_context():
            db.session.remove()
            for table in reversed(db.metadata.sorted_tables):
                if table.name not in ["lots", "frameworks", "framework_lots"]:
                    db.engine.execute(table.delete())
            FrameworkLot.query.filter(FrameworkLot.framework_id >= 100).delete()
            Framework.query.filter(Framework.id >= 100).delete()
            db.session.commit()
            db.get_engine(self.app).dispose()


class JSONTestMixin(object):
    """
    Tests to verify that endpoints that accept JSON.
    """
    endpoint = None
    method = None
    client = None

    def open(self, **kwargs):
        return self.client.open(
            self.endpoint.format(self=self),
            method=self.method,
            **kwargs
        )

    def test_non_json_causes_failure(self):
        response = self.open(
            data='this is not JSON',
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid JSON',
                  response.get_data())

    def test_invalid_content_type_causes_failure(self):
        response = self.open(
            data='{"services": {"foo": "bar"}}')

        assert_equal(response.status_code, 400)
        assert_in(b'Unexpected Content-Type', response.get_data())


class JSONUpdateTestMixin(JSONTestMixin):
    def test_missing_updated_by_should_fail_with_400(self):
        response = self.open(
            data='{}',
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in("'updated_by' is a required property", response.get_data(as_text=True))
