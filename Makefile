SHELL := /bin/bash
VIRTUALENV_ROOT := $(shell [ -z $$VIRTUAL_ENV ] && echo $$(pwd)/venv || echo $$VIRTUAL_ENV)

run_all: requirements run_migrations run_app

run_app: virtualenv
	${VIRTUALENV_ROOT}/bin/python application.py runserver

run_migrations: virtualenv
	${VIRTUALENV_ROOT}/bin/python application.py db upgrade

virtualenv:
	[ -z $$VIRTUAL_ENV ] && [ ! -d venv ] && virtualenv venv || true

bootstrap: virtualenv
	./scripts/bootstrap.sh

requirements: virtualenv requirements.txt
	${VIRTUALENV_ROOT}/bin/pip install -r requirements.txt

requirements_for_test: virtualenv requirements_for_test.txt
	${VIRTUALENV_ROOT}/bin/pip install -r requirements_for_test.txt

requirements_freeze:
	${VIRTUALENV_ROOT}/bin/pip install --upgrade pip
	${VIRTUALENV_ROOT}/bin/pip install --upgrade -r requirements_for_test.txt
	${VIRTUALENV_ROOT}/bin/pip freeze | grep -v marketplace-api.git > requirements.txt
	sed '/^-e /s/-e //' -i requirements.txt

test: test_pep8 test_migrations test_unit

test_pep8: virtualenv
	${VIRTUALENV_ROOT}/bin/pep8 .

lint:
	flake8 app
	flake8 tests

test_migrations: virtualenv
	${VIRTUALENV_ROOT}/bin/python ./scripts/list_migrations.py 1>/dev/null

test_unit: virtualenv
	${VIRTUALENV_ROOT}/bin/py.test ${PYTEST_ARGS}

.PHONY: virtualenv requirements requirements_for_test test_pep8 test_migrations test_unit test test_all run_migrations run_app run_all
