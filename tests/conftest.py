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


def _update_framework_status(request, app, slug, status):
    with app.app_context():
        framework = Framework.query.filter(
            Framework.slug == slug
        ).first()
        original_framework_status = framework.status
        framework.status = status

        db.session.add(framework)
        db.session.commit()

    def teardown():
        with app.app_context():
            framework = Framework.query.filter(
                Framework.slug == slug
            ).first()
            framework.status = original_framework_status

            db.session.add(framework)
            db.session.commit()

    request.addfinalizer(teardown)


def _add_framework(request, app, slug, status, framework, framework_agreement_details=None):
    if framework_agreement_details:
        framework_agreement_details = {'frameworkAgreementVersion': 'v1.0'}

    with app.app_context():
        framework = Framework(
            slug=slug,
            name=slug,
            framework=framework,
            framework_agreement_details=framework_agreement_details,
            status=status,
            clarification_questions_open=True if status == 'open' else False
        )
        db.session.add(framework)
        db.session.commit()

        def teardown():
            with app.app_context():
                framework = Framework.query.filter(Framework.slug == slug).first()
                Framework.query.filter(Framework.id == framework.id).delete()
                db.session.commit()

    request.addfinalizer(teardown)


def _base_framework(
        request, app, slug, status, framework, framework_agreement_details=None
):
    with app.app_context():
        if Framework.query.filter(Framework.slug == slug).first():
            _update_framework_status(request, app, slug=slug, status=status)
        else:
            _add_framework(
                request,
                app,
                slug=slug,
                status=status,
                framework=framework,
                framework_agreement_details=framework_agreement_details
            )


def _g8_framework(request, app, status):
    _base_framework(
        request, app, slug='g-cloud-8', status=status, framework='g-cloud', framework_agreement_details=True)


def _g7_framework(request, app, status):
    _base_framework(
        request, app, slug='g-cloud-7', status=status, framework='g-cloud', framework_agreement_details=False)


def _g6_framework(request, app, status):
    _base_framework(
        request, app, slug='g-cloud-6', status=status, framework='g-cloud', framework_agreement_details=False)


def _dos_framework(request, app, status):
    _base_framework(
        request,
        app,
        slug='digital-outcomes-and-specialists',
        status=status,
        framework='dos',
        framework_agreement_details=False
    )


# G8


@pytest.fixture()
def open_g8_framework(request, app):
    _g8_framework(request, app, status='open')


@pytest.fixture()
def live_g8_framework(request, app):
    _g8_framework(request, app, status='live')


# G6


@pytest.fixture()
def open_g6_framework(request, app):
    _g6_framework(request, app, status='open')


@pytest.fixture()
def expired_g6_framework(request, app):
    _g6_framework(request, app, status='expired')


# DOS


@pytest.fixture()
def open_dos_framework(request, app):
    _dos_framework(request, app, status='open')


@pytest.fixture()
def live_dos_framework(request, app):
    _dos_framework(request, app, status='live')


@pytest.fixture()
def expired_dos_framework(request, app):
    _dos_framework(request, app, status='expired')
