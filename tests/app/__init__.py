
from sqlbag import create_database

import os
from app import create_app, db
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy import inspect

from config import configs


def setup(dburi):
    print("Doing db setup")

    test_config = configs['test']
    test_config.SQLALCHEMY_DATABASE_URI = dburi

    app = create_app('test')
    Migrate(app, db)
    Manager(db, MigrateCommand)
    ALEMBIC_CONFIG = \
        os.path.join(os.path.dirname(__file__),
                     '../../migrations/alembic.ini')
    config = Config(ALEMBIC_CONFIG)
    config.set_main_option(
        "script_location",
        "migrations")
    with app.app_context():
        upgrade(config, 'head')
    print("Done db setup")
