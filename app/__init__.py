from functools import wraps
from flask import Flask
import logging
import dmapiclient
from dmutils import init_app, flask_featureflags

from config import configs

from .modelsbase import MySQLAlchemy as SQLAlchemy
from .modelsbase import enc, CustomEncoder
from . import logs

from .utils import log
from app.swagger import swag
from nplusone.ext.flask_sqlalchemy import NPlusOne
from sqltap.wsgi import SQLTapMiddleware


db = SQLAlchemy()

search_api_client = dmapiclient.SearchAPIClient()


def create_app(config_name):
    application = Flask(__name__)
    application.config['DM_ENVIRONMENT'] = config_name

    init_app(
        application,
        configs[config_name],
        db=db,
        search_api_client=search_api_client
    )

    if not application.config['DM_API_AUTH_TOKENS']:
        raise Exception("No DM_API_AUTH_TOKENS provided")

    # FIXME: The service broker adds a 'reconnect' parameter that's rejected by Postgres and
    # doesn't seem to be in the Postgres documentation anyway.  We need to patch the broker to fix
    # the username stability issue anyway.
    import os
    if 'DATABASE_URL' in os.environ:
        application.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace('reconnect=true', '')

    url_prefix = application.config['URL_PREFIX']
    url_prefix_v2 = application.config['URL_PREFIX_V2']
    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint, url_prefix=url_prefix)
    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint, url_prefix=url_prefix)
    from .auth import auth as auth_blueprint
    application.register_blueprint(auth_blueprint, url_prefix=url_prefix_v2)
    from .admin import blueprint as admin_blueprint
    application.register_blueprint(admin_blueprint.admin)

    application.json_encoder = CustomEncoder

    # maximum POST request length http://flask.pocoo.org/docs/0.12/patterns/fileuploads/#improving-uploads
    application.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 megabytes

    swag.init_app(application)

    if application.config['DEBUG']:
        # enable raise to raise exception on ORM misconfigured queries
        # application.config['NPLUSONE_RAISE'] = True
        application.config['NPLUSONE_LOGGER'] = logging.getLogger('app.nplusone')
        application.config['NPLUSONE_LOG_LEVEL'] = logging.ERROR
        NPlusOne(application)
        application.wsgi_app = SQLTapMiddleware(application.wsgi_app)

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
