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
    AUTH_REQUIRED = True
    DM_HTTP_PROTO = 'http'
    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_PLAIN_TEXT_LOGS = False
    DM_LOG_PATH = None
    DM_APP_NAME = 'api'
    DM_REQUEST_ID_HEADER = 'DM-Request-ID'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    FEATURE_FLAGS_TRANSACTION_ISOLATION = False

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    DM_API_BRIEFS_PAGE_SIZE = 100
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 100

    DM_API_PROJECTS_PAGE_SIZE = 100

    DM_ALLOWED_ADMIN_DOMAINS = ['digital.cabinet-office.gov.uk', 'crowncommercial.gov.uk', 'user.marketplace.team']

    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DM_FAILED_LOGIN_LIMIT = 5

    VCAP_SERVICES = None

    DM_FRAMEWORK_TO_ES_INDEX_MAPPING = {
        'g-cloud-9': {
            'services': 'g-cloud-9'
        },
        'digital-outcomes-and-specialists-2': {
            'briefs': 'briefs-digital-outcomes-and-specialists-2'
        }
    }


class Test(Config):
    SERVER_NAME = '127.0.0.1:5000'
    DM_SEARCH_API_AUTH_TOKEN = 'test'
    DM_SEARCH_API_URL = 'http://localhost'
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True
    ES_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace_test'
    DM_API_AUTH_TOKENS = 'myToken'
    DM_API_SERVICES_PAGE_SIZE = 5
    DM_API_SUPPLIERS_PAGE_SIZE = 5
    DM_API_BRIEFS_PAGE_SIZE = 5
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 5

    DM_API_PROJECTS_PAGE_SIZE = 5

    FEATURE_FLAGS_TRANSACTION_ISOLATION = enabled_since('2015-08-27')


class Development(Config):
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True

    DM_API_AUTH_TOKENS = 'myToken'
    DM_SEARCH_API_AUTH_TOKEN = 'myToken'
    DM_SEARCH_API_URL = 'http://localhost:5001'


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    DM_HTTP_PROTO = 'https'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'


class Preview(Live):
    FEATURE_FLAGS_TRANSACTION_ISOLATION = enabled_since('2015-08-27')


class Staging(Live):
    pass


class Production(Live):
    DM_ALLOWED_ADMIN_DOMAINS = ['digital.cabinet-office.gov.uk', 'crowncommercial.gov.uk']


configs = {
    'development': Development,
    'test': Test,

    'preview': Preview,
    'staging': Staging,
    'production': Production,
}
