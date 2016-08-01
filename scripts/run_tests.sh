#!/bin/bash
set -ex
pep8 .
./scripts/list_migrations.py
py.test
