from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix
from .flask_search_api_client.search_api_client import SearchApiClient
from dmutils import logging

from config import config


bootstrap = Bootstrap()
db = SQLAlchemy()
search_api_client = SearchApiClient()


def create_app(config_name):
    application = Flask(__name__)
    application.wsgi_app = ProxyFix(application.wsgi_app)
    application.config.from_object(config[config_name])

    config[config_name].init_app(application)

    logging.init_app(application)

    bootstrap.init_app(application)
    db.init_app(application)
    search_api_client.init_app(application)

    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint)
    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)
    if config[config_name].ALLOW_EXPLORER:
        from .explorer import explorer as explorer_blueprint
        application.register_blueprint(explorer_blueprint)

    return application
