SHELL := /bin/bash
VIRTUALENV_ROOT := $(shell [ -z $$VIRTUAL_ENV ] && echo $$(pwd)/venv || echo $$VIRTUAL_ENV)
DATABASE_HOST := localhost

.PHONY: run-all
run-all: requirements run-migrations run-app

.PHONY: run-app
run-app: virtualenv
	${VIRTUALENV_ROOT}/bin/flask run

.PHONY: run-migrations
run-migrations: virtualenv
	${VIRTUALENV_ROOT}/bin/flask db upgrade

.PHONY: virtualenv
virtualenv:
	[ -z $$VIRTUAL_ENV ] && [ ! -d venv ] && python3 -m venv venv || true

.PHONY: requirements
requirements: virtualenv test-requirements requirements.txt
	${VIRTUALENV_ROOT}/bin/pip install -r requirements.txt

.PHONY: requirements-dev
requirements-dev: virtualenv requirements-dev.txt
	${VIRTUALENV_ROOT}/bin/pip install -Ur requirements-dev.txt

.PHONY: freeze-requirements
freeze-requirements: virtualenv requirements-dev requirements-app.txt
	${VIRTUALENV_ROOT}/bin/python -m dmutils.repoutils.freeze_requirements requirements-app.txt

.PHONY: test
test: test-requirements test-flake8 test-migrations test-unit

.PHONY: test-bootstrap
test-bootstrap: virtualenv
	dropdb -h ${DATABASE_HOST} --if-exists digitalmarketplace_test
	createdb -h ${DATABASE_HOST} digitalmarketplace_test

.PHONY: test-requirements
test-requirements:
	@diff requirements-app.txt requirements.txt | grep '<' \
	    && { echo "requirements.txt doesn't match requirements-app.txt."; \
	         echo "Run 'make freeze-requirements' to update."; exit 1; } \
	    || { echo "requirements.txt is up to date"; exit 0; }

.PHONY: test-flake8
test-flake8: virtualenv requirements-dev
	${VIRTUALENV_ROOT}/bin/flake8 .

.PHONY: test-migrations
test-migrations: virtualenv requirements-dev
	${VIRTUALENV_ROOT}/bin/python ./scripts/list_migrations.py 1>/dev/null

.PHONY: test-unit
test-unit: virtualenv requirements-dev
	${VIRTUALENV_ROOT}/bin/py.test ${PYTEST_ARGS}

.PHONY: docker-build
docker-build:
	$(if ${RELEASE_NAME},,$(eval export RELEASE_NAME=$(shell git describe)))
	@echo "Building a docker image for ${RELEASE_NAME}..."
	docker build -t digitalmarketplace/api --build-arg release_name=${RELEASE_NAME} .
	docker tag digitalmarketplace/api digitalmarketplace/api:${RELEASE_NAME}

.PHONY: docker-push
docker-push:
	$(if ${RELEASE_NAME},,$(eval export RELEASE_NAME=$(shell git describe)))
	docker push digitalmarketplace/api:${RELEASE_NAME}
