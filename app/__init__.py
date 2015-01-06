import re
import os

from flask import Flask
from flask.ext.bootstrap import Bootstrap

from config import config
from .lib.helpers import convert_to_boolean

bootstrap = Bootstrap()


def create_app(config_name):
    application = Flask(__name__)
    application.config.from_object(config[config_name])

    for name in config_attrs(config[config_name]):
        if name in os.environ:
            application.config[name] = convert_to_boolean(os.environ[name])

    config[config_name].init_app(application)

    bootstrap.init_app(application)

    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    return application


def config_attrs(config):
    """Returns config attributes from a Config object"""
    p = re.compile('^[A-Z_]+$')
    return filter(lambda attr: bool(p.match(attr)), dir(config))
