import os
from dmutils.status import get_version_label
from celery.schedules import crontab


CELERYBEAT_SCHEDULE = {
    'maintain-seller-email-list': {
        'task': 'app.tasks.mailchimp.sync_mailchimp_seller_list',
        'schedule': crontab(hour='*/4', minute=0)
    },
    'send-daily-seller-email': {
        'task': 'app.tasks.mailchimp.send_new_briefs_email',
        'schedule': crontab(hour=17, minute=0)
    },
    'send_document_expiry_reminder': {
        'task': 'app.tasks.mailchimp.send_document_expiry_reminder',
        'schedule': crontab(hour=6, minute=0)
    },
    'process_closed_briefs': {
        'task': 'app.tasks.brief_tasks.process_closed_briefs',
        'schedule': crontab(hour=6, minute=0)
    },
    'create_responses_zip_for_closed_briefs': {
        'task': 'app.tasks.brief_tasks.create_responses_zip_for_closed_briefs',
        'schedule': crontab(hour=18, minute=1)
    },
    'update_brief_metrics': {
        'task': 'app.tasks.brief_tasks.update_brief_metrics',
        'schedule': crontab(hour='*/1', minute=1)
    },
    'update_brief_response_metrics': {
        'task': 'app.tasks.brief_response_tasks.update_brief_response_metrics',
        'schedule': crontab(hour='*/2', minute=2)
    },
    'update_supplier_metrics': {
        'task': 'app.tasks.supplier_tasks.update_supplier_metrics',
        'schedule': crontab(hour='*/4', minute=4)
    },
    'sync_application_approvals_with_jira': {
        'task': 'app.tasks.jira.sync_application_approvals_with_jira',
        'schedule': crontab(day_of_week='mon-fri', hour='8-18/1', minute=45)
    }
}


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
    SESSION_COOKIE_SAMESITE = 'Lax'
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
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Vcap-Request-Id'
    DM_API_ADMIN_USERNAME = 'admin'
    DM_API_ADMIN_PASSWORD = None
    # API key auth
    DM_API_KEY_HEADER = 'X-Api-Key'

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

    JIRA_FIELD_CODES = {
        'ASSESSOR_RESULT_CODES': {
            '1': ['customfield_11210', 'customfield_11208'],  # Strategy and Policy
            '2': ['customfield_11222', 'customfield_11221'],  # Change, Training and Transformation
            '3': ['customfield_11211', 'customfield_11212'],  # User research and Design
            '4': ['customfield_11213', 'customfield_11214'],  # Agile delivery and Governance
            '6': ['customfield_11215', 'customfield_11216'],  # Software engineering and Development
            '7': ['customfield_11220', 'customfield_11219'],  # Content and Publishing
            '8': ['customfield_11225', 'customfield_11226'],  # Cyber security
            '9': ['customfield_11223', 'customfield_11224'],  # Marketing, Communications and Engagement
            '10': ['customfield_11217', 'customfield_11218'],  # Support and Operations
            '11': ['customfield_11227', 'customfield_11228'],  # Data science
            '13': ['customfield_11230', 'customfield_11229'],  # Emerging technologies
            '14': ['customfield_11241', 'customfield_11242'],  # Change and Transformation
            '15': ['customfield_11243', 'customfield_11244']   # Training, Learning and Development
        },
        'MARKETPLACE_PROJECT_CODE': 'MARADMIN',
        'APPLICATION_FIELD_CODE': 'customfield_11100',
        'SUPPLIER_FIELD_CODE': 'customfield_11000',
        'RANKING_ASSESSOR_1_FIELD_CODE': 'customfield_11204',
        'RANKING_ASSESSOR_2_FIELD_CODE': 'customfield_11206'
    }

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
    DM_MAILCHIMP_NOREPLY_EMAIL = 'no-reply@digital.gov.au'
    DM_GENERIC_ADMIN_NAME = 'Digital Marketplace Admin'
    DM_GENERIC_SUPPORT_NAME = 'Digital Marketplace'

    RESET_PASSWORD_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    RESET_PASSWORD_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    RESET_PASSWORD_EMAIL_SUBJECT = 'Reset your Digital Marketplace password'

    INVITE_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    INVITE_EMAIL_FROM = 'no-reply@marketplace.digital.gov.au'
    INVITE_EMAIL_SUBJECT = 'Activate your new Marketplace account'
    BUYER_INVITE_MANAGER_CONFIRMATION_SUBJECT = 'Digital Marketplace buyer account request [SEC=UNCLASSIFIED]'
    BUYER_INVITE_REQUEST_ADMIN_EMAIL = 'marketplace+buyer-request@digital.gov.au'

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

    GENERIC_EMAIL_DOMAINS = ['bigpond.com', 'digital.gov.au', 'gmail.com', 'hotmail.com', 'icloud.com',
                             'iinet.net.au', 'internode.on.net', 'live.com.au', 'me.com', 'msn.com',
                             'optusnet.com.au', 'outlook.com', 'outlook.com.au', 'ozemail.com.au',
                             'tpg.com.au', 'y7mail.com', 'yahoo.com', 'yahoo.com.au']

    FRONTEND_ADDRESS = 'https://dm-dev.apps.y.cld.gov.au'
    ADMIN_ADDRESS = 'https://dm-dev-admin.apps.y.cld.gov.au'
    APP_ROOT = {'digital-marketplace': '/2'}

    SEND_EMAILS = True
    CSRF_ENABLED = True
    BASIC_AUTH = False

    ALLOWED_EXTENSIONS = ['pdf', 'odt', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']

    S3_BUCKET_NAME = ''
    S3_ENDPOINT_URL = 's3-ap-southeast-2.amazonaws.com'
    AWS_DEFAULT_REGION = ''
    SWAGGER = {'title': 'Digital Marketplace API', 'uiversion': 3}
    AWS_S3_URL = None
    AWS_SES_URL = None
    AWS_SQS_BROKER_URL = None
    AWS_SQS_QUEUE_URL = None

    # CELERY
    CELERY_TIMEZONE = 'Australia/Sydney'
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
    SEND_EMAILS = False


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

    JIRA_FEATURES = False

    DM_SEND_EMAIL_TO_STDERR = True
    SEND_EMAILS = True
    SECRET_KEY = 'DevKeyDevKeyDevKeyDevKeyDevKeyDevKeyDevKeyX='
    FRONTEND_ADDRESS = 'http://localhost:8000'
    BASIC_AUTH = True
    AWS_S3_URL = 'http://localhost:4572'
    AWS_SES_URL = 'http://localhost:4579'
    AWS_SQS_BROKER_URL = 'sqs://@localhost:4576'
    AWS_SQS_QUEUE_URL = 'http://localhost:4576/queue/dta-marketplace-local'
    AWS_SQS_QUEUE_NAME = 'dta-marketplace-local'
    CELERYBEAT_SCHEDULE = CELERYBEAT_SCHEDULE


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


class Preview(Live):
    # List all your feature flags below
    FEATURE_FLAGS = {
        'TRANSACTION_ISOLATION': True
    }


class Staging(Development):
    JIRA_FEATURES = True
    BASIC_AUTH = True
    DM_SEND_EMAIL_TO_STDERR = False
    CELERYBEAT_SCHEDULE = {}


class Production(Live):
    CELERYBEAT_SCHEDULE = CELERYBEAT_SCHEDULE


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'production': Production,
}
