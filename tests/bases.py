from nose.tools import assert_equal, assert_in

from app import create_app, db
from app.models import Framework, FrameworkLot, BuyerEmailDomain


class WSGIApplicationWithEnvironment(object):
    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs

    def __call__(self, environ, start_response):
        for key, value in self.kwargs.items():
            environ[key] = value
        return self.app(environ, start_response)


class BaseApplicationTest(object):

    config = None

    def setup(self):
        self.app = create_app('test')
        self.app.wsgi_app = WSGIApplicationWithEnvironment(
            self.app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(self.app.config['DM_API_AUTH_TOKENS'])
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            # Ensure there is at least one pre-approved buyer domain
            if BuyerEmailDomain.query.filter(BuyerEmailDomain.domain_name == 'digital.gov.uk').count() == 0:
                db.session.add(BuyerEmailDomain(domain_name='digital.gov.uk'))
                db.session.commit()

    def teardown(self):
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
