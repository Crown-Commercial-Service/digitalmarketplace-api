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

requirements-dev: virtualenv requirements-dev.txt
	${VIRTUALENV_ROOT}/bin/pip install -r requirements-dev.txt

compile-requirements:
	virtualenv venv-freeze
	$$(pwd)/venv-freeze/bin/pip install -r requirements-app.txt
	echo '# This file is autogenerated. Run `make compile-requirements`' > requirements.txt
	echo '# to update it with any changes made in requirements-app.txt' >> requirements.txt
	echo '' >> requirements.txt
	cat requirements-app.txt >> requirements.txt
	echo '' >> requirements.txt
	$$(pwd)/venv-freeze/bin/pip freeze -r requirements-app.txt | sed -n '/The following requirements were added by pip freeze/,$$p' >> requirements.txt
	rm -rf venv-freeze

test: test_pep8 test_migrations test_unit

test_pep8: virtualenv
	${VIRTUALENV_ROOT}/bin/pep8 .

test_migrations: virtualenv
	${VIRTUALENV_ROOT}/bin/python ./scripts/list_migrations.py 1>/dev/null

test_unit: virtualenv
	${VIRTUALENV_ROOT}/bin/py.test ${PYTEST_ARGS}

docker-build:
	$(if ${RELEASE_NAME},,$(eval export RELEASE_NAME=$(shell git describe)))
	@echo "Building a docker image for ${RELEASE_NAME}..."
	docker build -t digitalmarketplace/api --build-arg release_name=${RELEASE_NAME} .
	docker tag digitalmarketplace/api digitalmarketplace/api:${RELEASE_NAME}

docker-push:
	$(if ${RELEASE_NAME},,$(eval export RELEASE_NAME=$(shell git describe)))
	docker push digitalmarketplace/api:${RELEASE_NAME}


.PHONY: virtualenv requirements requirements-dev compile-requirements test_pep8 test_migrations test_unit test test_all run_migrations run_app run_all docker-build docker-push
