#!/usr/bin/env python

import os
from app import create_app, db
from flask.ext.script import Manager, Server
from flask.ext.migrate import Migrate, MigrateCommand

application = create_app(os.getenv('FLASH_CONFIG') or 'development')
manager = Manager(application)
manager.add_command("runserver", Server(port=5000))
migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
