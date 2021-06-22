import pytest
import os
import json
import io
import mock

from app import create_app
from app.models import db, Framework, Application


from sqlbag import temporary_database
from migrations import \
    load_from_app_model, load_test_fixtures


@pytest.fixture(autouse=True, scope='session')
def db_initialization(request):
    from config import configs

    with temporary_database() as dburi:
        test_config = configs['test']
        test_config.SQLALCHEMY_DATABASE_URI = dburi

        load_from_app_model(dburi)
        load_test_fixtures(dburi)

        yield


@pytest.fixture(scope='session')
def app(request):
    return create_app('test')


@pytest.fixture()
def app_context():
    app = create_app('test')
    with app.app_context() as c:
        yield c


def application_json_examples():
    FOLDER_PATH = 'tests/DATA/applications'

    for fname in os.listdir(FOLDER_PATH):
        with io.open(os.path.join(FOLDER_PATH, fname)) as f:
            yield json.loads(f.read())


@pytest.fixture(params=application_json_examples())
def sample_submitted_application(app, request):
    with mock.patch('app.models.get_marketplace_jira'):
        with app.app_context():
            application = Application(
                data=request.param,
            )

            db.session.add(application)
            db.session.flush()

            application.submit_for_approval()
            db.session.commit()

            yield application


@pytest.fixture()
def live_framework(request, app, status='live'):
    with app.app_context():
        framework = Framework.query.filter(
            Framework.slug == 'digital-outcomes-and-specialists'
        ).first()
        original_framework_status = framework.status
        framework.status = status

        db.session.add(framework)
        db.session.commit()

    def teardown():
        with app.app_context():
            framework = Framework.query.filter(
                Framework.slug == 'digital-outcomes-and-specialists'
            ).first()
            framework.status = original_framework_status

            db.session.add(framework)
            db.session.commit()

    request.addfinalizer(teardown)


@pytest.fixture()
def expired_framework(request, app):
    with app.app_context():
        framework = Framework.query.filter(
            Framework.slug == 'digital-outcomes-and-specialists'
        ).first()

        original_framework_status = framework.status
        framework.status = 'expired'
        db.session.add(framework)
        db.session.commit()

    def teardown():
        with app.app_context():
            framework = Framework.query.filter(
                Framework.slug == 'digital-outcomes-and-specialists'
            ).first()
            framework.status = original_framework_status

            db.session.add(framework)
            db.session.commit()

    request.addfinalizer(teardown)
