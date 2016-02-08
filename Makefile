SHELL := /bin/bash

run_all: requirements run_migrations run_app

run_app: virtualenv
	python application.py runserver

run_migrations: virtualenv
	python application.py db upgrade

virtualenv:
	[ -z $$VIRTUAL_ENV ] && virtualenv venv || true

bootstrap: virtualenv
	./scripts/bootstrap.sh

requirements: virtualenv requirements.txt
	pip install -r requirements.txt

requirements_for_test: virtualenv requirements_for_test.txt
	pip install -r requirements_for_test.txt

test: test_pep8 test_migrations test_unit

test_pep8: virtualenv
	pep8 .

test_migrations: virtualenv
	./scripts/list_migrations.py 1>/dev/null

test_unit: virtualenv
	py.test ${PYTEST_ARGS}

.PHONY: virtualenv requirements requirements_for_test test_pep8 test_migrations test_unit test test_all run_migrations run_app run_all
