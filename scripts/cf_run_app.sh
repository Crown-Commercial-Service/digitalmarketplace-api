#!/bin/bash

eval $(./scripts/ups_as_envs.py)
NEW_RELIC_CONFIG_FILE=newrelic.ini exec newrelic-admin run-program python wsgi.py
