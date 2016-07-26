#!/bin/bash
pep8 .
./scripts/list_migrations.py
py.test
