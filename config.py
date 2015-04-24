import os
import re

from flask._compat import string_types

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    DM_SEARCH_API_URL = None
    DM_SEARCH_API_AUTH_TOKEN = None
    ES_ENABLED = True
    ALLOW_EXPLORER = True
    AUTH_REQUIRED = True

    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_APP_NAME = 'api'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'
    DM_REQUEST_ID_HEADER = 'DM-Request-ID'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'

    @classmethod
    def init_app(cls, app):
        for name in config_attrs(cls):
            if name in os.environ:
                app.config[name] = convert_to_boolean(os.environ[name])


class Test(Config):
    DM_SEARCH_API_AUTH_TOKEN = 'test'
    DM_SEARCH_API_URL = 'http://localhost'
    DEBUG = True
    ES_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace_test'
    DM_API_SERVICES_PAGE_SIZE = 5
    DM_API_SUPPLIERS_PAGE_SIZE = 5


class Development(Config):
    DEBUG = True


class Live(Config):
    DEBUG = False
    ALLOW_EXPLORER = False


config = {
    'development': Development,
    'preview': Live,
    'staging': Live,
    'production': Live,
    'test': Test,
}


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
