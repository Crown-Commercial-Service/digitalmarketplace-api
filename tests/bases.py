from flask.testing import FlaskClient

from app import create_app, db
from app.models import Framework, FrameworkLot


class TestClient(FlaskClient):
    """This is a custom Test Client for handling the creation of a dedicated application context on a per request basis.

    Flask-SQLAlchemy attaches its db operations to the top application context on the context stack.
    Requests use the top application context on the context stack or create a new one if none exists.

    Normally this isn't an issue. Each new request in production will use its own thread and
    on finding that there is no existing application context will create a new one.

    In tests however we require an application context to create/ update the database with the data required for the
    test. We can then end up using this polluted application context in the view we're testing if we don't pop it. In
    the open method of this class we create a fresh application context for the request/ view to use and remove it
    after so it doesn't leak back to the test.
    """

    def open(self, *args, **kwargs):
        db.session.close()
        app_context = self.application.app_context()
        app_context.push()

        res = super(TestClient, self).open(*args, **kwargs)

        db.session.expire_all()
        app_context.pop()

        return res


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
        self.wsgi_app_main = WSGIApplicationWithEnvironment(
            self.app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(self.app.config['DM_API_AUTH_TOKENS']),
            REMOTE_ADDR='127.0.0.1',
        )
        self.wsgi_app_callbacks = WSGIApplicationWithEnvironment(
            self.app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(self.app.config['DM_API_CALLBACK_AUTH_TOKENS']),
            REMOTE_ADDR='127.0.0.1',
        )
        self.app.wsgi_app = self.wsgi_app_main
        self.app.test_client_class = TestClient
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown(self):
        db.session.remove()
        for table in reversed(db.metadata.sorted_tables):
            if table.name not in ["lots", "frameworks", "framework_lots"]:
                db.engine.execute(table.delete())
        FrameworkLot.query.filter(FrameworkLot.framework_id >= 100).delete()
        Framework.query.filter(Framework.id >= 100).delete()

        # Remove any framework variation details
        frameworks = db.session.query(Framework).filter(Framework.framework_agreement_details is not None)
        for framework in frameworks.all():
            framework.framework_agreement_details = None
            db.session.add(framework)

        db.session.commit()
        db.get_engine(self.app).dispose()
        self.app_context.pop()


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

        assert response.status_code == 400
        assert b'Invalid JSON' in response.get_data()

    def test_invalid_content_type_causes_failure(self):
        response = self.open(
            data='{"services": {"foo": "bar"}}')

        assert response.status_code == 400
        assert b'Unexpected Content-Type' in response.get_data()


class JSONUpdateTestMixin(JSONTestMixin):
    def test_missing_updated_by_should_fail_with_400(self):
        response = self.open(
            data='{}',
            content_type='application/json')

        assert response.status_code == 400
        assert "'updated_by' is a required property" in response.get_data(as_text=True)
