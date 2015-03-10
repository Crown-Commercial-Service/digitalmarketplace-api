import re
import os

from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix

from config import config
from .helpers import convert_to_boolean


bootstrap = Bootstrap()
db = SQLAlchemy()


def create_app(config_name):
    application = Flask(__name__)
    application.wsgi_app = ProxyFix(application.wsgi_app)
    application.config.from_object(config[config_name])

    for name in config_attrs(config[config_name]):
        if name in os.environ:
            application.config[name] = convert_to_boolean(os.environ[name])

    config[config_name].init_app(application)

    bootstrap.init_app(application)
    db.init_app(application)

    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint)
    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)
    if config[config_name].ALLOW_EXPLORER:
        from .explorer import explorer as explorer_blueprint
        application.register_blueprint(explorer_blueprint)

    return application


def config_attrs(config):
    """Returns config attributes from a Config object"""
    p = re.compile('^[A-Z_]+$')
    return filter(lambda attr: bool(p.match(attr)), dir(config))
