import re
import os

from flask import Flask
from flask._compat import string_types
from flask.ext.script import Manager
from flask.ext.bootstrap import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix
from flask.ext.migrate import Migrate, MigrateCommand

from config import config

bootstrap = Bootstrap()
db = SQLAlchemy()


def create_app(config_name):
    application = Flask(__name__)
    application.wsgi_app = ProxyFix(application.wsgi_app)
    application.config.from_object(config[config_name])
    migrate = Migrate(application, db)

    manager = Manager(db, MigrateCommand)

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


def convert_to_boolean(value):
    """Turn strings to bools if they look like them

    Truthy things should be True
    >>> for truthy in ['true', 'on', 'yes', '1']:
    ...   assert convert_to_boolean(truthy) == True

    Falsey things should be False
    >>> for falsey in ['false', 'off', 'no', '0']:
    ...   assert convert_to_boolean(falsey) == False

    Other things should be unchanged
    >>> for value in ['falsey', 'other', True, 0]:
    ...   assert convert_to_boolean(value) == value
    """
    if isinstance(value, string_types):
        if value.lower() in ['t', 'true', 'on', 'yes', '1']:
            return True
        elif value.lower() in ['f', 'false', 'off', 'no', '0']:
            return False

    return value
