#!/bin/bash
set -ex
pep8 app
pep8 tests
./scripts/list_migrations.py
py.test --cov=app --cov-report term-missing --cov-report=html:${CIRCLE_ARTIFACTS-.}/htmlcov
