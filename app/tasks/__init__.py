from flask import Flask
from .celery import make_celery
from config import configs
from os import getenv
from app.modelsbase import MySQLAlchemy as SQLAlchemy


def get_flask_app():
    config_name = getenv('DM_ENVIRONMENT') or 'development'
    app = Flask(__name__)
    app.config['DM_ENVIRONMENT'] = config_name
    app.config.from_object(configs[config_name])
    return app

db = SQLAlchemy()
flask_app = get_flask_app()
db.init_app(flask_app)
celery = make_celery(flask_app)
