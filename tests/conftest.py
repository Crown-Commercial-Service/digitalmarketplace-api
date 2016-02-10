from __future__ import absolute_import

import pytest

from .app import setup, teardown

from app import create_app
from app.models import db, Framework

from .example_listings import * # noqa


@pytest.fixture(autouse=True, scope='session')
def db_migration(request):
    setup()
    request.addfinalizer(teardown)


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
