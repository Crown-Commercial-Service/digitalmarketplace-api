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
    DM_LOG_LEVEL = 'INFO'
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
    DM_API_SUPPLIERS_PAGE_SIZE = 10
    DM_API_BRIEFS_PAGE_SIZE = 100
    DM_API_BRIEF_RESPONSES_PAGE_SIZE = 100
    DM_API_USER_PAGE_SIZE = 100
    DM_API_PAGE_SIZE = 100
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql:///digitalmarketplace'
    BASE_TEMPLATE_DATA = {}

    DM_FAILED_LOGIN_LIMIT = 5

    VCAP_SERVICES = None

    DEADLINES_TZ_NAME = 'Australia/Sydney'
    DEFAULT_REQUIREMENTS_DURATION = '2 weeks'
    DEADLINES_TIME_OF_DAY = '18:00:00'

    JIRA_URL = 'https://govausites.atlassian.net'
    JIRA_CREDS = ''
    JIRA_CREDS_OAUTH = ''

    JIRA_MARKETPLACE_PROJECT_CODE = 'MARADMIN'
    JIRA_APPLICATION_FIELD_CODE = 'customfield_11100'
    JIRA_SUPPLIER_FIELD_CODE = 'customfield_11000'

    JIRA_FEATURES = False

    ROLLBAR_TOKEN = None
    DM_TEAM_SLACK_WEBHOOK = None

    LEGACY_ROLE_MAPPING = True

    SEARCH_MINIMUM_MATCH_SCORE_NAME = 0
    SEARCH_MINIMUM_MATCH_SCORE_SUMMARY = 0.02

    # EMAIL CONFIG
    DM_SEND_EMAIL_TO_STDERR = False

    DM_CLARIFICATION_QUESTION_EMAIL = 'no-reply@marketplace.digital.gov.au'
    DM_FRAMEWORK_AGREEMENTS_EMAIL = 'enquiries@example.com'

    GENERIC_CONTACT_EMAIL = 'marketplace@digital.gov.au'
    DM_GENERIC_NOREPLY_EMAIL = 'no-reply@marketplace.digital.gov.au'
    DM_GENERIC_ADMIN_NAME = 'Digital Marketplace Admin'
    DM_GENERIC_SUPPORT_NAME = 'Digital Marketplace'

    RESET_PASSWORD_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    RESET_PASSWORD_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    RESET_PASSWORD_EMAIL_SUBJECT = 'Reset your Digital Marketplace password'

    INVITE_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    INVITE_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    INVITE_EMAIL_SUBJECT = 'Activate your new Marketplace account'

    NEW_SUPPLIER_INVITE_SUBJECT = 'Digital Marketplace - invitation to create seller account'

    CLARIFICATION_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    CLARIFICATION_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    CLARIFICATION_EMAIL_SUBJECT = 'Thanks for your clarification question'
    DM_FOLLOW_UP_EMAIL_TO = 'digitalmarketplace@mailinator.com'

    CREATE_USER_SUBJECT = 'Create your Digital Marketplace account'
    SECRET_KEY = None
    SHARED_EMAIL_KEY = None
    RESET_PASSWORD_SALT = 'ResetPasswordSalt'
    SUPPLIER_INVITE_TOKEN_SALT = 'SupplierInviteEmail'

    GENERIC_EMAIL_DOMAINS = ['gmail.com', 'bigpond.com', 'outlook.com', 'outlook.com.au', 'hotmail.com', 'yahoo.com',
                             'optusnet.com.au', 'msn.com', 'internode.on.net', 'iinet.net.au', 'ozemail.com.au',
                             'live.com.au', 'digital.gov.au', 'icloud.com']

    FRONTEND_ADDRESS = 'https://dm-dev.apps.staging.digital.gov.au'
    ADMIN_ADDRESS = 'https://dm-dev-admin.apps.staging.digital.gov.au'

    SEND_EMAILS = True


class Test(Config):
    DM_SEARCH_API_AUTH_TOKEN = 'test'
    DM_SEARCH_API_URL = 'http://localhost'
    DM_LOG_LEVEL = 'WARN'
    DEBUG = True
    ES_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql:///digitalmarketplace_test'
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

    DM_SEND_EMAIL_TO_STDERR = True


class Development(Config):
    DEBUG = True

    DM_API_AUTH_TOKENS = 'myToken'
    DM_SEARCH_API_AUTH_TOKEN = 'myToken'
    DM_SEARCH_API_URL = 'http://localhost:5001'
    DM_API_ADMIN_PASSWORD = 'admin'
    DM_LOG_LEVEL = 'INFO'

    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False
    }

    JIRA_FEATURES = True

    SEND_EMAILS = True


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    DM_HTTP_PROTO = 'https'

    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False
    }

    FRONTEND_ADDRESS = 'https://marketplace.service.gov.au'
    ADMIN_ADDRESS = 'https://dm-admin.apps.platform.digital.gov.au'

    SEND_EMAILS = True


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
