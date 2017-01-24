from __future__ import absolute_import

import pytest

from app import create_app
from app.models import db, Framework


from sqlbag import temporary_database, S

from .app import setup


@pytest.fixture(autouse=True, scope='session')
def db_initialization(request):
    with temporary_database() as dburi:
        with S(dburi) as s:
            s.execute('create extension if not exists pg_trgm;')
        setup(dburi)
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
