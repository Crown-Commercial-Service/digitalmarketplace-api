import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    ALLOW_EXPLORER = True
    AUTH_REQUIRED = True
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace'

    @staticmethod
    def init_app(app):
        pass


class Test(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/digitalmarketplace_test'


class Development(Config):
    DEBUG = True


class Live(Config):
    DEBUG = False
    ALLOW_EXPLORER = False


config = {
    'live': Live,
    'development': Development,
    'test': Test,
}
