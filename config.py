

class Config:
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

    DM_API_SERVICES_PAGE_SIZE = 100
    DM_API_SUPPLIERS_PAGE_SIZE = 100
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'


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
    DM_API_SERVICES_PAGE_SIZE = 5


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
