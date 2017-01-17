import os
from dmutils.status import enabled_since, get_version_label


class Config:
    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DM_SEARCH_API_URL = None
    DM_SEARCH_API_AUTH_TOKEN = None
    DM_API_AUTH_TOKENS = None
    ELASTICSEARCH_HOST = os.getenv('DM_ELASTICSEARCH_URL', 'localhost:9200')
    DM_API_ELASTICSEARCH_INDEX_SUFFIX = ''
    ES_ENABLED = True
    AUTH_REQUIRED = True
    DM_HTTP_PROTO = 'http'
    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_LOG_PATH = None
    DM_APP_NAME = 'api'
    DM_REQUEST_ID_HEADER = 'DM-Request-ID'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'
    DM_API_ADMIN_USERNAME = 'admin'
    DM_API_ADMIN_PASSWORD = None

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    # List all your feature flags below
    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False
    }

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    DM_API_BRIEFS_PAGE_SIZE = 100
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 100
    DM_API_USER_PAGE_SIZE = 100
    DM_API_PAGE_SIZE = 100
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'
    BASE_TEMPLATE_DATA = {}

    DM_FAILED_LOGIN_LIMIT = 5

    VCAP_SERVICES = None

    DEADLINES_TZ_NAME = 'Australia/Sydney'
    DEFAULT_REQUIREMENTS_DURATION = '2 weeks'
    DEADLINES_TIME_OF_DAY = '18:00:00'

    JIRA_URL = 'https://govausites.atlassian.net'
    JIRA_CREDS = ''
    JIRA_CREDS_OAUTH = ''

    JIRA_MARKETPLACE_PROJECT_CODE = 'JIRAPROJECT'
    JIRA_APPLICATION_FIELD_CODE = 'customfield_99999'

    JIRA_FEATURES = False

    ROLLBAR_TOKEN = None


class Test(Config):
    DM_SEARCH_API_AUTH_TOKEN = 'test'
    DM_SEARCH_API_URL = 'http://localhost'
    DM_API_ELASTICSEARCH_INDEX_SUFFIX = '_test'
    DEBUG = True
    ES_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace_test'
    DM_API_AUTH_TOKENS = 'myToken'
    DM_API_SERVICES_PAGE_SIZE = 5
    DM_API_SUPPLIERS_PAGE_SIZE = 5
    DM_API_BRIEFS_PAGE_SIZE = 5
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 5
    DM_API_PAGE_SIZE = 5
    # List all your feature flags below
    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': True
    }
    DM_API_ADMIN_USERNAME = None
    JIRA_URL = 'http://jira.example.com'
    JIRA_CREDS = 'a:b'
    JIRA_CREDS_OAUTH = 'at,ats,ck,kc'

    JIRA_FEATURES = True


class Development(Config):
    DEBUG = True

    DM_API_AUTH_TOKENS = 'myToken'
    DM_API_ELASTICSEARCH_INDEX_SUFFIX = '_dev'
    DM_SEARCH_API_AUTH_TOKEN = 'myToken'
    DM_SEARCH_API_URL = 'http://localhost:5001'
    DM_API_ADMIN_PASSWORD = 'admin'

    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False
    }

    JIRA_MARKETPLACE_PROJECT_CODE = 'MARADMIN'
    JIRA_APPLICATION_FIELD_CODE = 'customfield_11000'


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    DM_HTTP_PROTO = 'https'

    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False,
    }


class Preview(Live):
    # List all your feature flags below
    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': True
    }


class Staging(Development):
    JIRA_FEATURES = True


class Production(Live):
    pass


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'production': Production,
}
