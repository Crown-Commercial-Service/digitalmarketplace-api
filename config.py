import os
import re
from .app.helpers import convert_to_boolean

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    AUTH_REQUIRED = True
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'
    RDS_DB_NAME = None
    RDS_USERNAME = None
    RDS_PASSWORD = None
    RDS_HOSTNAME = None
    RDS_PORT = None

    @classmethod
    def init_app(cls, app):
        app.config.from_object(cls)
        for name in config_attrs(cls):
            if name in os.environ:
                app.config[name] = convert_to_boolean(os.environ[name])
        if cls._should_build_db_uri(app):
            uri = 'postgresql://{}:{}@{}:{}/{}'.format(
                app.config['RDS_USERNAME'], app.config['RDS_PASSWORD'],
                app.config['RDS_HOSTNAME'], app.config['RDS_PORT'],
                app.config['RDS_DB_NAME'])

            app.config['SQLALCHEMY_DATABASE_URI'] = uri

    @classmethod
    def _should_build_db_uri(cls, app):
        if 'SQLALCHEMY_DATABASE_URI' in os.environ:
            return False
        if app.config['RDS_DB_NAME'] is not None:
            return True
        return False


class Test(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace_test'


class Development(Config):
    DEBUG = True


class Live(Config):
    DEBUG = False


def config_attrs(config):
    """Returns config attributes from a Config object"""
    p = re.compile('^[A-Z_]+$')
    return filter(lambda attr: bool(p.match(attr)), dir(config))


config = {
    'live': Live,
    'development': Development,
    'test': Test,
}
