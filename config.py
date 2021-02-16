import os
from dmutils.status import get_version_label


class Config:

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DM_SEARCH_API_URL = None
    DM_SEARCH_API_AUTH_TOKEN = None
    DM_API_AUTH_TOKENS = None
    DM_API_CALLBACK_AUTH_TOKENS = None
    ES_ENABLED = True
    AUTH_REQUIRED = True
    DM_HTTP_PROTO = 'http'
    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_PLAIN_TEXT_LOGS = False
    DM_LOG_PATH = None
    DM_APP_NAME = 'api'

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    DM_API_BRIEFS_PAGE_SIZE = 100
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 100
    DM_API_BUYER_DOMAINS_PAGE_SIZE = 100
    DM_API_PROJECTS_PAGE_SIZE = 100
    DM_API_OUTCOMES_PAGE_SIZE = 100

    DM_ALLOWED_ADMIN_DOMAINS = ['digital.cabinet-office.gov.uk', 'crowncommercial.gov.uk', 'user.marketplace.team',
                                'notifications.service.gov.uk']

    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # If you are changing failed login limit, remember to update NO_ACCOUNT_MESSAGE in user-frontend
    DM_FAILED_LOGIN_LIMIT = 5

    VCAP_SERVICES = None

    DM_FRAMEWORK_TO_ES_INDEX = {
        'g-cloud-9': {
            'services': 'g-cloud-9'
        },
        'g-cloud-10': {
            'services': 'g-cloud-10'
        },
        'g-cloud-11': {
            'services': 'g-cloud-11'
        },
        'g-cloud-12': {
            'services': 'g-cloud-12'
        },
        'digital-outcomes-and-specialists': {
            'briefs': 'briefs-digital-outcomes-and-specialists'
        },
        'digital-outcomes-and-specialists-2': {
            'briefs': 'briefs-digital-outcomes-and-specialists'
        },
        'digital-outcomes-and-specialists-3': {
            'briefs': 'briefs-digital-outcomes-and-specialists'
        },
        'digital-outcomes-and-specialists-4': {
            'briefs': 'briefs-digital-outcomes-and-specialists'
        },
        'digital-outcomes-and-specialists-5': {
            'briefs': 'briefs-digital-outcomes-and-specialists'
        },
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
    DM_API_CALLBACK_AUTH_TOKENS = 'myCallbackToken'
    DM_API_SERVICES_PAGE_SIZE = 5
    DM_API_SUPPLIERS_PAGE_SIZE = 5
    DM_API_BRIEFS_PAGE_SIZE = 5
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 5

    DM_API_PROJECTS_PAGE_SIZE = 5


class Development(Config):
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True

    DM_API_AUTH_TOKENS = 'myToken'
    DM_API_CALLBACK_AUTH_TOKENS = 'myToken'
    DM_SEARCH_API_AUTH_TOKEN = 'myToken'
    DM_SEARCH_API_URL = f"http://localhost:{os.getenv('DM_SEARCH_API_PORT', 5009)}"


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    DM_HTTP_PROTO = 'https'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'


class Preview(Live):
    pass


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
