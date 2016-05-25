# digitalmarketplace-api

[![Build Status](https://travis-ci.org/alphagov/digitalmarketplace-api.svg?branch=master)](https://travis-ci.org/alphagov/digitalmarketplace-api)
[![Coverage Status](https://coveralls.io/repos/alphagov/digitalmarketplace-api/badge.svg?branch=master&service=github)](https://coveralls.io/github/alphagov/digitalmarketplace-api?branch=master)
[![Requirements Status](https://requires.io/github/alphagov/digitalmarketplace-api/requirements.svg?branch=master)](https://requires.io/github/alphagov/digitalmarketplace-api/requirements/?branch=master)

API tier for Digital Marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Quickstart

Install [Virtualenv](https://virtualenv.pypa.io/en/latest/)
```
sudo easy_install virtualenv
```

Bootstrap the database
```
make bootstrap
```

Install dependencies, run migrations and run the app
```
make run_all
```

## Full setup

Install [Virtualenv](https://virtualenv.pypa.io/en/latest/)

```
sudo easy_install virtualenv
```

Ensure you have Postgres running locally, and then bootstrap your development
environment

```
make bootstrap
```

On Debian Jessie, the following packages are required for bootstrapping to work:

```
apt-get install gcc virtualenv python-dev libffi-dev libpq-dev
```

### Activate the virtual environment

```
source ./venv/bin/activate
```

### Upgrade database schema

When new database migrations are added you can bring your local database schema
up to date by running upgrade.

```make run_migrations```

### Upgrade dependencies

Install new Python dependencies with pip

```make requirements_for_test```

### Run the tests

This will run the linter, validate the migrations and run the unit tests.

```make test```

To test individual parts of the test stack use the `test_pep8`, `test_migrations`
or `test_unit` targets.

### Run the development server

Run the API with environment variables required for local development set.
This will install requirements, run database migrations and run the app.

```make run_all```

To just run the application use the `run_app` target.

## Using the API locally

By default the API runs on port 5000. Calls to the API require a valid bearer 
token. Tokens to be accepted can be set using the DM_AUTH_TOKENS environment
variable (a colon-separated list), e.g.:

```export DM_API_AUTH_TOKENS=myToken1:myToken2```

If ``DM_API_AUTH_TOKENS`` is not explicitly set then the run_api.sh script sets
it to ``myToken``. You should include a valid token in your request headers, 
e.g.:

```
curl -i -H "Authorization: Bearer myToken" 127.0.0.1:5000/services/123456789
```

## Using FeatureFlags

To use feature flags, check out the documentation in (the README of)
[digitalmarketplace-utils](https://github.com/alphagov/digitalmarketplace-utils#using-featureflags).


## Utility scripts

### Getting a list of migration versions

`./scripts/list_migrations.py` checks that there are no branches in the DB migrations and prints a
list of migration versions

### Getting a list of application URLs

`python application.py list_routes` prints a full list of registered application URLs with supported HTTP methods
