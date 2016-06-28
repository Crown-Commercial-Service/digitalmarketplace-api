#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from dmutils import init_manager
from flask.ext.migrate import Migrate, MigrateCommand

from app import create_app, db


port = int(os.getenv('PORT', '5000'))
application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')
manager = init_manager(application, port, ['./json_schemas'])

migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)

application.logger.info('Command line: {}'.format(sys.argv))

if __name__ == '__main__':
    try:
        application.logger.info('Running manager')
        manager.run()
    finally:
        application.logger.info('Manager finished')
