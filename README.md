# Digital Marketplace API

![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)

API application for Digital Marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

This app provides an interface for our Postgres database backing service, using the SQLAlchemy ORM.

## Quickstart

It's recommended to use the [DM Runner](https://github.com/alphagov/digitalmarketplace-runner)
tool, which will install and run the app (and a Postgres instance) as part of the full suite of apps.

If you want to run the app as a stand-alone process, you'll need to set the `SQLALCHEMY_DATABASE_URI` env variable
to your own local Postgres instance. See the [Developer Manual](https://alphagov.github.io/digitalmarketplace-manual/developing-the-digital-marketplace/developer-setup.html)
for more details.

You can then clone the repo and run:

```
make run-all
```

This command will install dependencies and start the app.

By default, the app will be served at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Using the API

Calls to the API require a valid bearer token. Tokens to be accepted can be set
using the `DM_AUTH_TOKENS` environment variable (a colon-separated list), for example:

```export DM_API_AUTH_TOKENS=myToken1:myToken2```

If `DM_API_AUTH_TOKENS` is not explicitly set then the run script sets
it to `myToken`. You should include a valid token in your request headers,
for example:

```
curl -i -H "Authorization: Bearer myToken" 127.0.0.1:5000/services
```

POST requests will require a `Content-Type` header, set to `application/json`.

## Testing

Run the full test suite:

```
make test
```

To only run the Python tests:

```
make test-unit
```

To run the `flake8` linter:

```
make test-flake8
```

To re-create an empty test database without migrations (this is a useful troubleshooting step if you are having issues with the test database):

```
make test-bootstrap
```

### Updating test API model stubs
The tests validate API responses against the model stubs in https://github.com/Crown-Commercial-Service/digitalmarketplace-test-utils/tree/main/dmtestutils/api_model_stubs. To update these, point the API requirements-dev to a branch of `digitalmarketplace-test-utils`. Once your changes are approved in a PR you should make a new release of `digitalmarketplace-test-utils` and update the version in `digitalmarketplace-api` to use it.


### Updating Python dependencies

`requirements.txt` file is generated from the `requirements.in` in order to pin
versions of all nested dependencies. If `requirements.in` has been changed (or
we want to update the unpinned nested dependencies) `requirements.txt` should be
regenerated with

```
make freeze-requirements
```

`requirements.txt` should be committed alongside `requirements.in` changes.

## Migrations

## Creating a new database migration

After editing `models.py` to add/edit/remove models for the database, you'll need to generate a new migration script.

The easiest way to do this is to run

```
flask db migrate --rev-id <revision_id> -m '<description>'
```

Our revision IDs increment by 10 each time. Check the output of `flask db show` to find the current
revision.

Until you apply the migration, you can delete the generated revision and
re-generate it as you need to.

To apply new migrations:

```make run-migrations```

### Getting a list of migration versions

`./scripts/list_migrations.py` checks that there are no branches in the DB migrations and prints a
list of migration versions.

## Utility scripts

### Getting a list of application URLs

`flask routes` prints a full list of registered application URLs with supported HTTP methods.


### Model schemas

`app/generate_model_schemas.py` uses the `alchemyjsonschema` library to generate reference schemas of our database models.

Note that the `alchemyjsonschema` library is a dev requirement only.

## Contributing

This repository is maintained by the Digital Marketplace team at the [Crown Commercial Service](https://github.com/Crown-Commercial-Service).

If you have a suggestion for improvement, please raise an issue on this repo.

### Reporting Vulnerabilities

If you have discovered a security vulnerability in this code, we appreciate your help in disclosing it to us in a
responsible manner.

Please follow the [CCS vulnerability reporting steps](https://www.crowncommercial.gov.uk/about-ccs/vulnerability-disclosure-policy/),
giving details of any issue you find. Appropriate credit will be given to those reporting confirmed issues.

## Licence

Unless stated otherwise, the codebase is released under [the MIT License][mit].
This covers both the codebase and any sample code in the documentation.

The documentation is [&copy; Crown copyright][copyright] and available under the terms
of the [Open Government 3.0][ogl] licence.

[mit]: LICENCE
[copyright]: http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/uk-government-licensing-framework/crown-copyright/
[ogl]: http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
