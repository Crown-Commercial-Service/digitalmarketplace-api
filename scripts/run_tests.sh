#!/bin/bash
set -ex
pep8 app
pep8 tests
py.test --cov=app --cov-report term-missing --cov-report=html:${CIRCLE_ARTIFACTS-.}/htmlcov
