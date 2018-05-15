from flask import Flask
from .celery import make_celery
from config import configs
from os import getenv, environ
from app.modelsbase import MySQLAlchemy as SQLAlchemy
from dmutils import rollbar_agent


def get_flask_app():
    config_name = getenv('DM_ENVIRONMENT') or 'development'
    app = Flask(__name__)
    app.config['DM_ENVIRONMENT'] = config_name
    app.config['ROLLBAR_TOKEN'] = getenv('ROLLBAR_TOKEN')
    app.config.from_object(configs[config_name])
    # FIXME: The service broker adds a 'reconnect' parameter that's rejected by Postgres and
    # doesn't seem to be in the Postgres documentation anyway.  We need to patch the broker to fix
    # the username stability issue anyway.
    if 'DATABASE_URL' in environ:
        app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URL'].replace('reconnect=true', '')
    return app

db = SQLAlchemy(session_options={'autocommit': True})
flask_app = get_flask_app()
db.init_app(flask_app)
rollbar_agent.init_app(flask_app)
celery = make_celery(flask_app)
