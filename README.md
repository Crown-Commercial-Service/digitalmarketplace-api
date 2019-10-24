# digitalmarketplace-api

[![Build Status](https://travis-ci.org/alphagov/digitalmarketplace-api.svg?branch=master)](https://travis-ci.org/alphagov/digitalmarketplace-api)
[![Coverage Status](https://coveralls.io/repos/alphagov/digitalmarketplace-api/badge.svg?branch=master&service=github)](https://coveralls.io/github/alphagov/digitalmarketplace-api?branch=master)
[![Requirements Status](https://requires.io/github/alphagov/digitalmarketplace-api/requirements.svg?branch=master)](https://requires.io/github/alphagov/digitalmarketplace-api/requirements/?branch=master)
![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)

API tier for Digital Marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Quickstart

Bootstrap the database
```
make bootstrap
```

Install dependencies, run migrations and run the app
```
make run-all
```

## Full setup

Ensure you have Postgres running locally, and then bootstrap your development
environment

```
make bootstrap
```

On Debian Jessie, the following packages are required for bootstrapping to work:

```
apt-get install gcc python3-dev libffi-dev libpq-dev python3-venv
```

### Activate the virtual environment

```
source ./venv/bin/activate
```

### Upgrade database schema

When new database migrations are added you can bring your local database schema
up to date by running upgrade.

```make run-migrations```

### Upgrade dependencies

Install new Python dependencies with pip

```make requirements-dev```

### Run the tests

This will run the linter, validate the migrations and run the unit tests.

```make test```

To test individual parts of the test stack use the `test-flake8`, `test-migrations`
or `test-unit` targets.

### Run the development server

Run the API with environment variables required for local development set.
This will install requirements, run database migrations and run the app.

```make run-all```

To just run the application use the `run-app` target.

## Using the API locally

By default the API runs on port 5000. Calls to the API require a valid bearer 
token. Tokens to be accepted can be set using the DM_AUTH_TOKENS environment
variable (a colon-separated list), e.g.:

```export DM_API_AUTH_TOKENS=myToken1:myToken2```

If ``DM_API_AUTH_TOKENS`` is not explicitly set then the run script sets
it to ``myToken``. You should include a valid token in your request headers, 
e.g.:

```
curl -i -H "Authorization: Bearer myToken" 127.0.0.1:5000/services
```

## Updating application dependencies

`requirements.txt` file is generated from the `requirements-app.txt` in order to pin
versions of all nested dependencies. If `requirements-app.txt` has been changed (or
we want to update the unpinned nested dependencies) `requirements.txt` should be
regenerated with

```
make freeze-requirements
```

`requirements.txt` should be commited alongside `requirements-app.txt` changes.

## Creating a new database migration

After editing `models.py` to add/edit/remove models for the database, you'll need to generate a new migration script.
The easiest way to do this is to run `flask db migrate --rev-id <revision_id> -m '<description'>`. Our
revision IDs increment by 10 each time; check the output of `flask db show` to find the current
revision. Until you run the migration to update the database state, you can delete the generated revision and
re-generate it as you need to.

## Utility scripts

### Getting a list of migration versions

`./scripts/list_migrations.py` checks that there are no branches in the DB migrations and prints a
list of migration versions

### Getting a list of application URLs

`flask routes` prints a full list of registered application URLs with supported HTTP methods


## Model schemas

`app/generate_model_schemas.py` uses the `alchemyjsonschema` library to generate reference schemas of our database models.
Note that the `alchemyjsonschema` library is a dev requirement only.

