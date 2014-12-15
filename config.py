import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    CONFIG_PROPERTY = "some_property"
    AUTH_TOKENS_PATH = ""

    @staticmethod
    def init_app(app):
        pass


class Test(Config):
    DEBUG = True
    AUTH_TOKENS_PATH = "./config/tokens"


class Development(Config):
    DEBUG = True
    AUTH_TOKENS_PATH = "./config/tokens"


class Live(Config):
    DEBUG = False


config = {
    'live': Live,
    'development': Development,
    'test': Test,
}
