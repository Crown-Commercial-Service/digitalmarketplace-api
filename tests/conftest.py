import pytest

from .app import setup, teardown


@pytest.fixture(autouse=True, scope='session')
def db_migration(request):
    setup()
    request.addfinalizer(teardown)
