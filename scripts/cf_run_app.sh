#!/bin/sh

NEW_RELIC_CONFIG_FILE=newrelic.ini exec newrelic-admin run-program python application.py runprodserver
