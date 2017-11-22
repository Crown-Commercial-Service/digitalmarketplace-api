from functools import wraps
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import json
from sqlalchemy import MetaData

import dmapiclient
from dmutils import init_app, flask_featureflags

from config import configs
from .converters import DataUnobscuringConverter

db = SQLAlchemy(metadata=MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}))
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

    if not application.config['DM_API_AUTH_TOKENS']:
        raise Exception("No DM_API_AUTH_TOKENS provided")

    if application.config['VCAP_SERVICES']:
        cf_services = json.loads(application.config['VCAP_SERVICES'])
        application.config['SQLALCHEMY_DATABASE_URI'] = cf_services['postgres'][0]['credentials']['uri']

    application.url_map.converters.update({"obscured": DataUnobscuringConverter})

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
