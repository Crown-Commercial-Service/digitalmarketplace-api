#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from dmutils import init_manager
from flask_migrate import Migrate, MigrateCommand

from app import create_app, db

from sqlbag import S, load_sql_from_file


port = int(os.getenv('PORT', '5000'))
application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')
manager = init_manager(application, port, ['./json_schemas'])

migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)

application.logger.info('Command line: {}'.format(sys.argv))

dburl = application.config['SQLALCHEMY_DATABASE_URI']


def do_startup():
    with S(dburl, echo=False) as s:
        load_sql_from_file(s, 'DB/data/on_startup.sql')


if __name__ == '__main__':
    try:
        do_startup()
        application.logger.info('Running manager')
        manager.run()
    finally:
        application.logger.info('Manager finished')
