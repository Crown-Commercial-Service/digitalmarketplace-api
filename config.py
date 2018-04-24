import os
from dmutils.status import get_version_label
from celery.schedules import crontab


class Config:
    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    URL_PREFIX = '/api'
    URL_PREFIX_V2 = '/api/2'
    SESSION_COOKIE_NAME = 'dm_session'
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
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

    DM_API_APPLICATIONS_PAGE_SIZE = 1000
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
    DM_TEAM_EMAIL = None
    DM_TEAM_SLACK_WEBHOOK = None

    LEGACY_ROLE_MAPPING = False

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
    ORAMS_GENERIC_SUPPORT_NAME = 'ORAMS'

    RESET_PASSWORD_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    RESET_PASSWORD_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    RESET_PASSWORD_EMAIL_SUBJECT = 'Reset your Digital Marketplace password'
    ORAMS_RESET_PASSWORD_EMAIL_SUBJECT = 'Reset your ORAMS password'

    INVITE_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    INVITE_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    INVITE_EMAIL_SUBJECT = 'Activate your new Marketplace account'
    ORAMS_INVITE_EMAIL_SUBJECT = 'Create your ORAMS Portal account'
    BUYER_INVITE_MANAGER_CONFIRMATION_SUBJECT = 'Digital Marketplace buyer account request [SEC=UNCLASSIFIED]'
    BUYER_INVITE_REQUEST_ADMIN_EMAIL = 'marketplace+buyer-request@digital.gov.au'
    ORAMS_BUYER_INVITE_REQUEST_ADMIN_EMAIL = 'nick.ball+bcc@digital.gov.au'

    NEW_SUPPLIER_INVITE_SUBJECT = 'Digital Marketplace - invitation to create seller account'

    CLARIFICATION_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    CLARIFICATION_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    CLARIFICATION_EMAIL_SUBJECT = 'Thanks for your clarification question'
    DM_FOLLOW_UP_EMAIL_TO = 'digitalmarketplace@mailinator.com'

    CREATE_USER_SUBJECT = 'Create your Digital Marketplace account'
    SECRET_KEY = None
    SHARED_EMAIL_KEY = None
    RESET_PASSWORD_SALT = 'ResetPasswordSalt'
    SIGNUP_INVITATION_TOKEN_SALT = 'NewUserInviteEmail'
    BUYER_CREATION_TOKEN_SALT = 'BuyerCreation'
    SUPPLIER_INVITE_TOKEN_SALT = 'SupplierInviteEmail'

    GENERIC_EMAIL_DOMAINS = ['gmail.com', 'bigpond.com', 'outlook.com', 'outlook.com.au', 'hotmail.com', 'yahoo.com',
                             'optusnet.com.au', 'msn.com', 'internode.on.net', 'iinet.net.au', 'ozemail.com.au',
                             'live.com.au', 'digital.gov.au', 'icloud.com', 'me.com']

    FRONTEND_ADDRESS = 'https://dm-dev.apps.y.cld.gov.au'
    ADMIN_ADDRESS = 'https://dm-dev-admin.apps.y.cld.gov.au'
    APP_ROOT = {'digital-marketplace': '/2', 'orams': '/orams'}

    SEND_EMAILS = True
    CSRF_ENABLED = False
    BASIC_AUTH = False

    ALLOWED_EXTENSIONS = ['pdf', 'odt', 'doc', 'docx']

    S3_BUCKET_NAME = ''
    S3_ENDPOINT_URL = 's3-ap-southeast-2.amazonaws.com'
    AWS_DEFAULT_REGION = ''
    SWAGGER = {'title': 'Digital Marketplace API', 'uiversion': 3}
    ORAMS_FRAMEWORK = 'orams'

    # CELERY
    CELERY_ASYNC_TASKING_ENABLED = True
    CELERY_TIMEZONE = 'UTC'
    CELERYBEAT_SCHEDULE = {}


class Test(Config):
    URL_PREFIX = ''
    URL_PREFIX_V2 = '/2'
    DM_SEARCH_API_AUTH_TOKEN = 'test'
    DM_SEARCH_API_URL = 'http://localhost'
    DM_LOG_LEVEL = 'WARN'
    DEBUG = True
    ES_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql:///digitalmarketplace_test'
    DM_API_AUTH_TOKENS = 'myToken'
    DM_API_APPLICATIONS_PAGE_SIZE = 5
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
    SECRET_KEY = 'TestKeyTestKeyTestKeyTestKeyTestKeyTestKeyX='
    CSRF_FAKED = False
    BASIC_AUTH = True
    DEADLINES_TZ_NAME = 'Australia/Sydney'

    CELERY_ASYNC_TASKING_ENABLED = False


class Development(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

    DM_API_AUTH_TOKENS = 'myToken'
    DM_SEARCH_API_AUTH_TOKEN = 'myToken'
    DM_SEARCH_API_URL = 'http://localhost:5001'
    DM_API_ADMIN_PASSWORD = 'admin'
    DM_LOG_LEVEL = 'INFO'

    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False
    }

    JIRA_FEATURES = True

    DM_SEND_EMAIL_TO_STDERR = True
    SEND_EMAILS = True
    SECRET_KEY = 'DevKeyDevKeyDevKeyDevKeyDevKeyDevKeyDevKeyX='
    FRONTEND_ADDRESS = 'http://localhost:8000'
    BASIC_AUTH = True

    CELERY_ASYNC_TASKING_ENABLED = False


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    DM_HTTP_PROTO = 'https'

    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': False
    }

    FRONTEND_ADDRESS = 'https://marketplace.service.gov.au'
    ADMIN_ADDRESS = 'https://dm-admin.apps.b.cld.gov.au'

    SEND_EMAILS = True
    ORAMS_BUYER_INVITE_REQUEST_ADMIN_EMAIL = 'orams@ato.gov.au'


class Preview(Live):
    # List all your feature flags below
    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': True
    }


class Staging(Development):
    JIRA_FEATURES = True
    BASIC_AUTH = True
    CELERY_ASYNC_TASKING_ENABLED = True
    DM_SEND_EMAIL_TO_STDERR = False


class Production(Live):
    CELERYBEAT_SCHEDULE = {
        'maintain-seller-email-list': {
            'task': 'app.tasks.mailchimp.sync_mailchimp_seller_list',
            'schedule': crontab(hour='*/4', minute=0)
        },
        'send-daily-seller-email': {
            'task': 'app.tasks.mailchimp.send_new_briefs_email',
            'schedule': crontab(hour=7, minute=0)
        },
        'process_closed_briefs': {
            'task': 'app.tasks.brief_tasks.process_closed_briefs',
            'schedule': crontab(hour=20)
        }
    }


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'production': Production,
}
