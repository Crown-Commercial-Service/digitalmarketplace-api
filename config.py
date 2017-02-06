import os
from dmutils.status import enabled_since, get_version_label


class Config:

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DM_SEARCH_API_URL = None
    DM_SEARCH_API_AUTH_TOKEN = None
    DM_API_AUTH_TOKENS = None
    ES_ENABLED = True
    ALLOW_EXPLORER = True
    AUTH_REQUIRED = True
    DM_HTTP_PROTO = 'http'
    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_LOG_PATH = None
    DM_APP_NAME = 'api'
    DM_REQUEST_ID_HEADER = 'DM-Request-ID'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    FEATURE_FLAGS_TRANSACTION_ISOLATION = False
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = False

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    DM_API_BRIEFS_PAGE_SIZE = 100
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 100
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'

    DM_FAILED_LOGIN_LIMIT = 5

    VCAP_SERVICES = None


class Test(Config):
    DM_SEARCH_API_AUTH_TOKEN = 'test'
    DM_SEARCH_API_URL = 'http://localhost'
    DEBUG = True
    ES_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace_test'
    DM_API_AUTH_TOKENS = 'myToken'
    DM_API_SERVICES_PAGE_SIZE = 5
    DM_API_SUPPLIERS_PAGE_SIZE = 5
    DM_API_BRIEFS_PAGE_SIZE = 5
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 5
    FEATURE_FLAGS_TRANSACTION_ISOLATION = enabled_since('2015-08-27')
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2016-11-29')


class Development(Config):
    DEBUG = True

    DM_API_AUTH_TOKENS = 'myToken'
    DM_SEARCH_API_AUTH_TOKEN = 'myToken'
    DM_SEARCH_API_URL = 'http://localhost:5001'

    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2016-11-29')


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    ALLOW_EXPLORER = False
    DM_HTTP_PROTO = 'https'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'


class Preview(Live):
    FEATURE_FLAGS_TRANSACTION_ISOLATION = enabled_since('2015-08-27')
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2017-02-06')


class Staging(Live):
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2017-02-07')


class Production(Live):
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2017-02-08')


configs = {
    'development': Development,
    'test': Test,

    'preview': Preview,
    'staging': Staging,
    'production': Production,
}
