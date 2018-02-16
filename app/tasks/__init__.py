from flask import Flask
from .celery import make_celery
from config import configs
from os import getenv
from app import create_app


def get_flask_app():
    config_name = getenv('DM_ENVIRONMENT') or 'development'
    app = Flask(__name__)
    app.config['DM_ENVIRONMENT'] = config_name
    app.config.from_object(configs[config_name])
    return app

flask_app = get_flask_app()
celery = make_celery(flask_app)
