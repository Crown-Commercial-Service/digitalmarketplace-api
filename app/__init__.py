from functools import wraps
from flask import Flask
from flask.ext.elasticsearch import FlaskElasticsearch
from flask.ext.sqlalchemy import SQLAlchemy
import json

import dmapiclient
from dmutils import init_app, flask_featureflags

from config import configs

db = SQLAlchemy()
es_client = FlaskElasticsearch()

search_api_client = dmapiclient.SearchAPIClient()
feature_flags = flask_featureflags.FeatureFlag()


def create_app(config_name):
    application = Flask(__name__)
    application.config['DM_ENVIRONMENT'] = config_name

    init_app(
        application,
        configs[config_name],
        db=db,
        feature_flags=feature_flags,
        search_api_client=search_api_client
    )

    es_client.init_app(application)

    if not application.config['DM_API_AUTH_TOKENS']:
        raise Exception("No DM_API_AUTH_TOKENS provided")

    # FIXME: The service broker adds a 'reconnect' parameter that's rejected by Postgres and
    # doesn't seem to be in the Postgres documentation anyway.  We need to patch the broker to fix
    # the username stability issue anyway.
    import os
    if 'DATABASE_URL' in os.environ:
        application.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace('reconnect=true', '')

    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint)
    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)

    return application


def isolation_level(level):
    """Return a Flask view decorator to set SQLAlchemy isolation level

    Usage::
        @view("/thingy/<id>", methods=["POST"])
        @isolation_level("SERIALIZABLE")
        def create_thing(id):
            ...
    """
    def decorator(view):
        @wraps(view)
        def view_wrapper(*args, **kwargs):
            if flask_featureflags.is_active('TRANSACTION_ISOLATION'):
                db.session.connection(execution_options={'isolation_level': level})
            return view(*args, **kwargs)
        return view_wrapper
    return decorator
