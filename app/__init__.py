from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
from dmutils import logging, config, apiclient, proxy_fix

from config import configs

bootstrap = Bootstrap()
db = SQLAlchemy()
search_api_client = apiclient.SearchAPIClient()


def create_app(config_name):
    application = Flask(__name__)
    application.config['DM_ENVIRONMENT'] = config_name
    application.config.from_object(configs[config_name])
    config.init_app(application)

    proxy_fix.init_app(application)
    logging.init_app(application)

    bootstrap.init_app(application)
    db.init_app(application)
    search_api_client.init_app(application)

    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint)
    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)

    if application.config['ALLOW_EXPLORER']:
        from .explorer import explorer as explorer_blueprint
        application.register_blueprint(explorer_blueprint)

    return application
