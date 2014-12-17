import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    CONFIG_PROPERTY = "some_property"
    AUTH_REQUIRED = True

    @staticmethod
    def init_app(app):
        pass


class Test(Config):
    DEBUG = True


class Development(Config):
    DEBUG = True


class Live(Config):
    DEBUG = False


config = {
    'live': Live,
    'development': Development,
    'test': Test,
}
