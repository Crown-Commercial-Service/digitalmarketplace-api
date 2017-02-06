from __future__ import absolute_import

import pytest

from app import create_app
from app.models import db, Framework


from sqlbag import temporary_database, S


from migrations import \
    load_from_app_model, load_test_fixtures, load_from_alembic_migrations


INIT_TEST_DB_WITH_ALEMBIC = True


@pytest.fixture(autouse=True, scope='session')
def db_initialization(request):
    from config import configs

    with temporary_database(do_not_delete=False) as dburi:
        test_config = configs['test']
        test_config.SQLALCHEMY_DATABASE_URI = dburi

        if INIT_TEST_DB_WITH_ALEMBIC:
            load_from_alembic_migrations(dburi)
        else:
            load_from_app_model(dburi)
            load_test_fixtures(dburi)

        yield


@pytest.fixture(scope='session')
def app(request):
    return create_app('test')


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
    return live_framework(request, app, status='expired')
