import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import MetaData

import dmapiclient
from dmutils.flask_init import init_app, api_error_handlers
from dmutils.flask import DMGzipMiddleware

from config import configs


db = SQLAlchemy(metadata=MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}))
search_api_client = dmapiclient.SearchAPIClient()


def create_app(config_name):
    application = Flask(__name__)
    application.config['DM_ENVIRONMENT'] = config_name

    init_app(
        application,
        configs[config_name],
        db=db,
        search_api_client=search_api_client,
        error_handlers=api_error_handlers,
    )

    if not application.config['DM_API_AUTH_TOKENS']:
        raise Exception("No DM_API_AUTH_TOKENS provided")

    if application.config['VCAP_SERVICES']:
        cf_services = json.loads(application.config['VCAP_SERVICES'])
        application.config['SQLALCHEMY_DATABASE_URI'] = (cf_services['postgres'][0]['credentials']['uri']
                                                         .replace('postgres://', "postgresql://", 1))

    from .metrics import metrics as metrics_blueprint, gds_metrics
    from .main import main as main_blueprint
    from .status import status as status_blueprint
    from .callbacks import callbacks as callbacks_blueprint

    application.register_blueprint(metrics_blueprint)
    application.register_blueprint(main_blueprint)
    application.register_blueprint(callbacks_blueprint, url_prefix='/callbacks')
    application.register_blueprint(status_blueprint)

    gds_metrics.init_app(application)

    DMGzipMiddleware(application, compress_by_default=False)

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
            db.session.connection(execution_options={'isolation_level': level})
            return view(*args, **kwargs)
        return view_wrapper
    return decorator
