# digitalmarketplace-api

API tier for Digital Marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Setup

Install [Virtualenv](https://virtualenv.pypa.io/en/latest/)

```
sudo easy_install virtualenv
```

Bootstrap you development environment

```
./scripts/bootstrap.sh
```

### Activate the virtual environment

```
source ./venv/bin/activate
```

### Run the tests

```
./scripts/run_tests.sh
```

### Run the development server

```
python application.py runserver
```

### Upgrade database schema

When new database migrations are added you can bring your local database schema
up to date by running upgrade.

```python applications.py db upgrade```

### Upgrade dependencies

Install new Python dependencies with pip

```pip install -r requirements_for_test.txt```

### Using the API locally

Calls to the API require a valid bearer token. Tokens to be accepted can be set using the AUTH_TOKENS environment variable, e.g.:

```set AUTH_TOKENS=myToken```

and then you can include this token in your request headers, e.g.:

```
curl -i -H "Authorization: Bearer myToken" 127.0.0.1:5000/services/123456789
```
