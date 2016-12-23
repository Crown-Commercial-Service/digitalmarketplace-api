from __future__ import absolute_import

from datetime import datetime
from itertools import product

import pytest
from six import iteritems, iterkeys

from app import create_app, db
from app.models import (
    Framework, SupplierFramework, Supplier, User, ContactInformation, DraftService, Lot, Service, FrameworkLot
)
from tests.app import setup, teardown


@pytest.fixture(autouse=True, scope='session')
def test_db(request):
    request.addfinalizer(teardown)
    return setup()


@pytest.fixture(scope='function')
def session(request, test_db):
    test_db.session.begin_nested()
    request.addfinalizer(test_db.session.rollback)


@pytest.fixture(autouse=True, scope='session')
def app(request):
    app = create_app('test')
    ctx = app.test_request_context()
    ctx.push()
    request.addfinalizer(ctx.pop)
    request._app = app
    return app


@pytest.fixture()
def draft_service(supplier_framework):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_framework['supplierId']
    ).first()
    framework = Framework.query.filter(
        Framework.slug == supplier_framework['frameworkSlug']
    ).first()
    lot = Lot.query.filter(Lot.slug == 'digital-specialists').first()

    ds = DraftService(
        framework=framework,
        lot=lot,
        service_id="1234567890",
        supplier=supplier,
        data={},
        status='submitted',
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.session.add_all([
        FrameworkLot(framework_id=framework.id, lot_id=lot.id),
        ds,
        Service.create_from_draft(ds, 'published')
    ])
    db.session.commit()
    return ds


@pytest.fixture()
def supplier():
    s = Supplier(
        supplier_id=None,
        name=u"Supplier name",
        description="",
        clients=[]
    )
    db.session.add(s)
    db.session.commit()

    return {'id': s.supplier_id}


@pytest.fixture(params=[{'on_framework': True}])
def supplier_framework(request, supplier, live_example_framework):
    sf = SupplierFramework(
        supplier_id=supplier['id'],
        framework_id=live_example_framework['id'],
        **request.param
    )
    db.session.add(sf)
    db.session.commit()

    return sf.serialize()


_framework_kwargs_whitelist = set(("status", "framework", "framework_agreement_details",))


def _update_framework(slug, **kwargs):
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

    return framework.serialize()


def _add_framework(slug, **kwargs):
    # first whitelist the kwargs to limit what we have to worry about
    kwargs = {k: v for k, v in iteritems(kwargs) if k in _framework_kwargs_whitelist}
    if "status" in kwargs and "clarification_questions_open" not in kwargs:
        kwargs["clarification_questions_open"] = (kwargs["status"] == "open")

    framework = Framework(slug=slug, name=slug, **kwargs)
    db.session.add(framework)
    db.session.commit()
    return framework.serialize()


def _framework_fixture_inner(slug, **kwargs):
    # we have to do a switch between two implementations here as in some cases a matching Framework
    # may already be in the database (e.g. Frameworks that were inserted by migrations)
    inner_func = (
        _update_framework if Framework.query.filter(Framework.slug == slug).first() else _add_framework
    )
    return inner_func(slug, **kwargs)

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
_example_framework_details = {
    "slug": "example-framework",
    "framework": "g-cloud",
    "framework_agreement_details": None
}


def _supplierframework_fixture_inner(sf_kwargs=None):
    sf_kwargs = sf_kwargs or {}
    supplier_framework_id_pairs = set()
    for framework, supplier in product(Framework.query.all(), Supplier.query.all()):
        supplier_framework = SupplierFramework(
            supplier=supplier,
            framework=framework,
            **sf_kwargs
        )
        supplier_framework_id_pairs.add((supplier.supplier_id, framework.id,))
        db.session.add(supplier_framework)

    db.session.commit()


def _supplier_fixture_inner(supplier_kwargs=None, ci_kwargs=None):
    supplier_kwargs = supplier_kwargs or {}
    supplier_kwargs = dict({
        "name": "Supplier {}".format(supplier_kwargs.get("supplier_id", "")),
        "description": "some description",
    }, **supplier_kwargs)

    supplier = Supplier(**supplier_kwargs)
    db.session.add(supplier)
    db.session.flush()

    ci_kwargs = ci_kwargs or {}
    ci_kwargs = dict({
        "contact_name": "Contact for supplier {}".format(supplier.supplier_id),
        "email": "{}@contact.com".format(supplier.supplier_id),
        "postcode": "SW1A 1AA",
        "supplier_id": supplier.supplier_id,
    }, **ci_kwargs)

    contact_information = ContactInformation(**ci_kwargs)
    db.session.add(contact_information)

    db.session.commit()

    supplier_id = supplier.supplier_id
    return supplier_id


def _user_fixture_inner(user_kwargs=None):
    user_kwargs = user_kwargs or {}
    user_kwargs = dict({
        "email_address": "test+{}@digital.gov.uk".format(user_kwargs.get("id", "replaceme")),
        "active": True,
        "password": "fake password",
        "password_changed_at": datetime.now(),
        "name": "my name",
    }, **user_kwargs)

    user = User(**user_kwargs)
    db.session.add(user)
    db.session.commit()

    # if we didn't know the user id at insert time and didn't have an email we should replace it now
    # so we don't end up with collisions
    if user.email_address == "test+replaceme@digital.gov.uk":
        user.email_address = "test+{}@digital.gov.uk".format(user.id)
        db.session.add(user)
        db.session.commit()

    user_id = user.id
    return user_id

# Frameworks


@pytest.fixture()
def open_example_framework():
    return _framework_fixture_inner(**dict(_example_framework_details, status="open"))


@pytest.fixture(params=[{}])
def live_example_framework(request):
    return _framework_fixture_inner(**dict(_example_framework_details, status="live", **request.param))


@pytest.fixture()
def open_g8_framework():
    return _framework_fixture_inner(**dict(_g8_framework_defaults, status="open"))


@pytest.fixture()
def live_g8_framework():
    return _framework_fixture_inner(**dict(_g8_framework_defaults, status="live"))


@pytest.fixture()
def live_g8_framework_2_variations():
    _framework_fixture_inner(**dict(
        _g8_framework_defaults,
        status="live",
        framework_agreement_details=dict(_generic_framework_agreement_details, variations={
            "banana": {
                "createdAt": "2016-06-06T20:01:34.000000Z",
            },
            "toblerone": {
                "createdAt": "2016-07-06T21:09:09.000000Z",
            },
        }),
    ))


@pytest.fixture()
def open_g6_framework(session):
    return _framework_fixture_inner(**dict(_g6_framework_defaults, status="open"))


@pytest.fixture()
def expired_g6_framework(session):
    return _framework_fixture_inner(**dict(_g6_framework_defaults, status="expired"))


@pytest.fixture()
def open_dos_framework(session):
    return _framework_fixture_inner(**dict(_dos_framework_defaults, status="open"))


@pytest.fixture()
def live_dos_framework(session):
    return _framework_fixture_inner(**dict(_dos_framework_defaults, status="live"))


@pytest.fixture()
def expired_dos_framework(session):
    return _framework_fixture_inner(**dict(_dos_framework_defaults, status="expired"))


# Suppliers


@pytest.fixture()
def supplier_basic():
    return _supplier_fixture_inner(supplier_kwargs={"supplier_id": 1})


@pytest.fixture()
def supplier_basic_alt():
    return _supplier_fixture_inner(supplier_kwargs={"supplier_id": 2})


# Users


@pytest.fixture()
def user_role_supplier(supplier_basic):
    return _user_fixture_inner(user_kwargs={
        "id": 1,
        "role": "supplier",
        "supplier_id": supplier_basic,
    })


@pytest.fixture()
def user_role_supplier_alt(supplier_basic_alt):
    return _user_fixture_inner(user_kwargs={
        "id": 2,
        "role": "supplier",
        "supplier_id": supplier_basic_alt,
    })


# Frameworks & Suppliers with some SupplierFrameworks setup


@pytest.fixture()
def live_g8_framework_2_variations_suppliers_not_on_framework(
        live_g8_framework_2_variations,
        user_role_supplier,
        ):
    _supplierframework_fixture_inner()


@pytest.fixture()
def live_g8_framework_2_variations_suppliers_on_framework(
        live_g8_framework_2_variations,
        user_role_supplier,
        ):
    _supplierframework_fixture_inner(sf_kwargs={"on_framework": True})


@pytest.fixture()
def live_g8_framework_2_variations_suppliers_on_framework_with_alt(
        live_g8_framework_2_variations, user_role_supplier, user_role_supplier_alt
    ):
    _supplierframework_fixture_inner(sf_kwargs={"on_framework": True})


@pytest.fixture()
def live_g8_framework_suppliers_on_framework(
        live_g8_framework,
        user_role_supplier,
        ):
    _supplierframework_fixture_inner(sf_kwargs={"on_framework": True})
