from invoke import task

from dmdevtools.invoke_tasks import (
    api_app_tasks,
    requirements_dev,
    virtualenv,
)


@task(virtualenv)
def run_migrations(c):
    """Upgrade database schema"""
    c.run(f"flask db upgrade")


@task(virtualenv, requirements_dev)
def test_migrations(c):
    """Check that migrations parse"""
    c.run("python scripts/list_migrations.py", hide=True)


@task(virtualenv)
def test_bootstrap(c, database_host="localhost"):
    """Create a clean database for testing"""
    c.run(f"dropdb -h {database_host} --if-exists digitalmarketplace_test")
    c.run(f"createdb -h {database_host} digitalmarketplace_test")


ns = api_app_tasks
ns.add_task(run_migrations)
ns.add_task(test_migrations)
ns.add_task(test_bootstrap)

# add run-migrations to run-all
ns["run-all"].pre.insert(1, run_migrations)

# add test-migrations to test
ns["test"].pre.insert(1, test_migrations)
