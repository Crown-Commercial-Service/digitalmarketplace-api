import os
from dmutils.status import enabled_since, get_version_label


class Config:

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DM_SEARCH_API_URL = None
    DM_SEARCH_API_AUTH_TOKEN = None
    ES_ENABLED = True
    ALLOW_EXPLORER = True
    AUTH_REQUIRED = True
    DM_HTTP_PROTO = 'http'
    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_APP_NAME = 'api'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'
    DM_REQUEST_ID_HEADER = 'DM-Request-ID'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'

    DM_FAILED_LOGIN_LIMIT = 5


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
    DM_HTTP_PROTO = 'https'


configs = {
    'development': Development,
    'preview': Live,
    'staging': Live,
    'production': Live,
    'test': Test,
}
