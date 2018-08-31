#!/usr/bin/env python

from __future__ import print_function

import os

from dmutils import init_manager
from flask_migrate import Migrate, MigrateCommand

from app import create_app, db


application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')
manager = init_manager(application, 5000, ['./json_schemas'])

migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
