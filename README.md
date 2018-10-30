# digitalmarketplace-api

[![Build Status](https://travis-ci.org/alphagov/digitalmarketplace-api.svg?branch=master)](https://travis-ci.org/alphagov/digitalmarketplace-api)
[![Coverage Status](https://coveralls.io/repos/alphagov/digitalmarketplace-api/badge.svg?branch=master&service=github)](https://coveralls.io/github/alphagov/digitalmarketplace-api?branch=master)
[![Requirements Status](https://requires.io/github/alphagov/digitalmarketplace-api/requirements.svg?branch=master)](https://requires.io/github/alphagov/digitalmarketplace-api/requirements/?branch=master)

API tier for Digital Marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Quickstart

You'll want to have a python `virtualenv` set up for installing and running the python dependencies within. Once you've created one of those and activated it, you can install the python requirements needed for development and testing with:

	make requirements_for_test

Create a local postgres database for development with:

	createdb digitalmarketplace

And initialize that database with:

 python migrations.py sync


## Full setup

Ensure you have Postgres running locally, and then bootstrap your development environment:

	make bootstrap

Some system-level libraries are required for the following packages to work. On Ubuntu you'll need at least the following:

	apt install gcc python-dev libffi-dev libpq-dev

### Docker

It is easier to have all services (Postgres, Localstack) running using docker-compose.

Just run `docker-compose up -d` in your api root.

### Upgrade database schema

This project is set up with some migration tooling that largely automates migrations.

It works a bit differently to regular rails-style migrations, so some background is required.

- All schema change code is centralized into two places
	- `migrations.py` for tasks
	- `DB/migrations` for the migration SQL itself

To sync up your development database from the model, simply run:

	python migrations.py sync

The changes necessary to sync your local database to the application schema will be generated and you'll be prompted to review and run them.

If you've removed/renamed columns in the application schema models, this can generate destructive changes, so make sure to do a careful review if you have data you need to keep in your local database.

#### Deploying migrations

For deployment, migration scripts need to be generated in advance, and placed in the pending folder.

A number of tasks exist in `migrations.py` for generating these files and checking the status of the various deployment environments (currently `staging` and `prod`).

In most cases you'll only need one file. But if staging and production get out of sync such that each needs different migrations applied, you'll need two file.

When you deploy, the build process runs `db_tasks.py` against the relevant database. This script is smart enough to figure out what migrations need applying, and tests they'll be applied correctly before actually running them on a real database.

The script works by testing various scenarios until it finds one that will result in a matching schema. In the situation where there are two migration files (eg m1.sql, m2.sql), the scenarios are considered in the following order.

	- 0 changes (ie no migrations needed)
	- 1 most recent changes (just m2.sql)
	- 2 most recent changes (m1.sql followed by m2.sql)

Additional files would result in further steps (files are assumed to be in lexographical order by file name).

At each step, two temporary databases will be created. One is populated with the current database state, the other with the target state. The relevant files are run and the result checked for correctness.

When a correct configuration is found, the migration is run for real against the actual database, and the script finishes. If no configuration results in correctness, the script exits with a failure code.

### Upgrading and freezing dependencies

Install new Python dependencies with pip:

	make requirements_for_test

The dependencies that are installed during actual deployment are installed from requirements.txt, which specifies exact package versions.

This file shouldn't be hand-edited. Instead, non-versioned requirements should be specified in:

	- setup.py: for dependencies of the application itself
	- requirements_for_test.txt: dependencies needed for running the tests

These requirements are *abstract*. To update requirements.txt with concrete, frozen requirements, first create a fresh, empty virtual environment


### Run the tests

This will run the linter, validate the migrations and run the unit tests.

  make test

To test individual parts of the test stack use the `test_pep8`, `test_migrations`
or `test_unit` targets.

### Run the development server

Run the API with environment variables required for local development set.
This will install requirements, run database migrations and run the app.

```make run_all```

To just run the application use the `run_app` target.

### Enable Celery tasking and run the Celery worker

The API will use asynchronous Celery for certain tasks (such as emailing).
Celery needs to be configured to use Amazon SQS or localstack for its broker, and requires various environment variables to be present in the API's execution environment for this to work:

#### Amazon SQS
```
export AWS_SQS_REGION='us-west-1'
export AWS_SQS_QUEUE_NAME='my-queue'
export AWS_SQS_QUEUE_URL='https://<region>.queue.amazonaws.com/<queue_account>/<queue_name>'
export AWS_SQS_BROKER_URL='sqs://[<MYACCESSKEYID>]:[<MYSECRETKEY>]@[localhost:4576]'
```

#### Localstack
In addition to Amazon SQS environment variables, the endpoint_url of boto3 needs to be overridden with the following environment variables
```
export AWS_S3_URL=http://localhost:4572
export AWS_SES_URL=http://localhost:4579
```

To add CRON like task scheduling, modify the config item `CELERYBEAT_SCHEDULE` to include your scheduled task. See [Celery Periodic Tasks - Entries](http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html) for more information on Celery beat tasks.

To start a Celery worker and the beat schedule, run the script `scripts/run_celery_worker_and_beat.sh` - this is designed to run in the foreground, and requires the same environment variables as above, as well as an optional var `CELERY_BEAT_SCHEDULE_FILE` which should contain a filesystem location for the schedule DB file. Note, because this includes the Celery beat schedule, you should only run one instance of this script.

## Using the API locally

By default the API runs on port 5000. Calls to the API require a valid bearer
token. Tokens to be accepted can be set using the DM_AUTH_TOKENS environment
variable (a colon-separated list), e.g.:

```export DM_API_AUTH_TOKENS=myToken1:myToken2```

If ``DM_API_AUTH_TOKENS`` is not explicitly set then the run_api.sh script sets
it to ``myToken``. You should include a valid token in your request headers,
e.g.:

```
curl -i -H "Authorization: Bearer myToken" 127.0.0.1:5000/services
```

## Using FeatureFlags

To use feature flags, check out the documentation in (the README of)
[digitalmarketplace-utils](https://github.com/alphagov/digitalmarketplace-utils#using-featureflags).


## Utility scripts

### Getting a list of application URLs

`python application.py list_routes` prints a full list of registered application URLs with supported HTTP methods

### Data import

Scripts in `scripts/importers` import data in csv format to the database through the API of a running instance.
See each script for usage information.

	./scripts/importers/import_suppliers.py http://data-api.example.com/ < 'example_listings/test_source_data/DMP Data Source - Test data.csv'
