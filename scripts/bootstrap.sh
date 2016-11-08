#!/bin/bash
#
# Bootstrap virtualenv environment and postgres databases locally.
#
# NOTE: This script expects to be run from the project root with
# ./scripts/bootstrap.sh

set -o pipefail

if [ ! $VIRTUAL_ENV ]; then
  virtualenv ./venv
  . ./venv/bin/activate
fi

# Some of the specified packages use syntax in their requirements.txt
# that older pips don't understand
pip install "pip>=8.0"

# Install Python development dependencies
pip install -r requirements_for_test.txt

# Create Postgres databases
createdb digitalmarketplace
createdb digitalmarketplace_test

# Upgrade databases
python application.py db upgrade
