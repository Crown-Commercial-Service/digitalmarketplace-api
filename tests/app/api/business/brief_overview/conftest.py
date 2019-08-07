import pytest
import mock

from flask_login import current_user
from app.models import Brief, Framework, Lot, WorkOrder


@pytest.fixture()
def framework():
    return Framework(id=1, slug='digital-marketplace')


@pytest.fixture()
def work_order():
    return WorkOrder(id=1)


@pytest.fixture()
def outcome_lot():
    return Lot(id=1, slug='digital-outcome', one_service_limit=True)


@pytest.fixture()
def specialist_lot():
    return Lot(id=1, slug='digital-professionals', one_service_limit=True)


@pytest.fixture()
def outcome_brief(framework, outcome_lot):
    return Brief(id=1, data={}, framework=framework, lot=outcome_lot, work_order=None)


@pytest.fixture()
def specialist_brief(framework, specialist_lot):
    return Brief(id=1, data={}, framework=framework, lot=specialist_lot, work_order=None)
