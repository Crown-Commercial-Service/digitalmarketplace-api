from __future__ import absolute_import

import pytest

from .app import setup, teardown

from app import create_app
from app.models import db, Framework, SupplierFramework


@pytest.fixture(autouse=True, scope='session')
def db_migration(request):
    setup()
    request.addfinalizer(teardown)


@pytest.fixture(scope='session')
def app(request):
    return create_app('test')


@pytest.fixture()
def add_g_cloud_8(request, app):
    with app.app_context():
        g_cloud_8 = Framework(
            slug='g-cloud-8',
            name='G-Cloud 8',
            framework='g-cloud',
            framework_agreement_details={'frameworkAgreementVersion': 'v1.0'},
            status='open',
            clarification_questions_open=False
        )
        db.session.add(g_cloud_8)
        db.session.commit()

        def teardown():
            with app.app_context():
                g_cloud_8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()
                Framework.query.filter(Framework.id == g_cloud_8.id).delete()
                # remove any suppliers registered to this framework
                SupplierFramework.query.filter(SupplierFramework.framework_id == g_cloud_8.id).delete()
                db.session.commit()

    request.addfinalizer(teardown)


@pytest.fixture(params=[('live', 'digital-outcomes-and-specialists')])
def update_framework_status(request, app):

    def _update_framework_status(request, app, status, framework_slug):
        with app.app_context():
            framework = Framework.query.filter(
                Framework.slug == framework_slug
            ).first()
            original_framework_status = framework.status
            framework.status = status

            db.session.add(framework)
            db.session.commit()

        def teardown():
            with app.app_context():
                framework = Framework.query.filter(
                    Framework.slug == framework_slug
                ).first()
                framework.status = original_framework_status

                db.session.add(framework)
                db.session.commit()

        request.addfinalizer(teardown)

    _update_framework_status(request, app, request.param[0], request.param[1])
