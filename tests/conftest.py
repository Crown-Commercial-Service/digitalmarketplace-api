from __future__ import absolute_import

from six import iteritems, iterkeys
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


_framework_kwargs_whitelist = set(("status", "framework", "framework_agreement_details",))


def _update_framework(request, app, slug, **kwargs):
    if not kwargs:
        # request doesn't really care about any more specific properties of the Framework. nothing for us
        # to do.
        return

    # first whitelist the kwargs to limit what we have to worry about
    kwargs = {k: v for k, v in iteritems(kwargs) if k in _framework_kwargs_whitelist}

    framework = Framework.query.filter(
        Framework.slug == slug
    ).first()
    original_values = {k: getattr(framework, k) for k in iterkeys(kwargs)}
    for k, v in iteritems(kwargs):
        setattr(framework, k, v)

    db.session.add(framework)
    db.session.commit()

    def teardown():
        with app.app_context():
            framework = Framework.query.filter(
                Framework.slug == slug
            ).first()
            for k, v in iteritems(original_values):
                setattr(framework, k, v)

            db.session.add(framework)
            db.session.commit()

    request.addfinalizer(teardown)


def _add_framework(request, app, slug, **kwargs):
    # first whitelist the kwargs to limit what we have to worry about
    kwargs = {k: v for k, v in iteritems(kwargs) if k in _framework_kwargs_whitelist}
    if "status" in kwargs and "clarification_questions_open" not in kwargs:
        kwargs["clarification_questions_open"] = (kwargs["status"] == "open")

    framework = Framework(slug=slug, name=slug, **kwargs)
    db.session.add(framework)
    db.session.commit()

    def teardown():
        with app.app_context():
            Framework.query.filter(Framework.slug == slug).delete()
            db.session.commit()

    request.addfinalizer(teardown)


def _framework_fixture_inner(request, app, slug, **kwargs):
    with app.app_context():
        # we have to do a switch between two implementations here as in some cases a matching Framework
        # may already be in the database (e.g. Frameworks that were inserted by migrations)
        inner_func = (
            _update_framework if Framework.query.filter(Framework.slug == slug).first() else _add_framework
        )
        inner_func(request, app, slug, **kwargs)

_generic_framework_agreement_details = {"frameworkAgreementVersion": "v1.0"}

_g8_framework_defaults = {
    "slug": "g-cloud-8",
    "framework": "g-cloud",
    "framework_agreement_details": _generic_framework_agreement_details,
}
_g7_framework_defaults = {
    "slug": "g-cloud-7",
    "framework": "g-cloud",
    "framework_agreement_details": None,
}
_g6_framework_defaults = {
    "slug": "g-cloud-6",
    "framework": "g-cloud",
    "framework_agreement_details": None,
}
_dos_framework_defaults = {
    "slug": "digital-outcomes-and-specialists",
    "framework": "dos",
    "framework_agreement_details": None,
}


# G8


@pytest.fixture()
def open_g8_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_g8_framework_defaults, status="open"))


@pytest.fixture()
def live_g8_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_g8_framework_defaults, status="live"))


# G6


@pytest.fixture()
def open_g6_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_g6_framework_defaults, status="open"))


@pytest.fixture()
def expired_g6_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_g6_framework_defaults, status="expired"))


# DOS


@pytest.fixture()
def open_dos_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_dos_framework_defaults, status="open"))


@pytest.fixture()
def live_dos_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_dos_framework_defaults, status="live"))


@pytest.fixture()
def expired_dos_framework(request, app):
    _framework_fixture_inner(request, app, **dict(_dos_framework_defaults, status="expired"))
