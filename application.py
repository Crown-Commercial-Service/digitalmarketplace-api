#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from dmutils import init_manager
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager, Command

from app import create_app, db


# FIXME: use a server like Waitress instead, and push this code into dmutils
class Server(Command):

    def __init__(self, app, port):
        self.app = app
        self.port = port

    def run(self):
        self.app.logger.info('Running server on port {}'.format(self.port))
        self.app.run(host='0.0.0.0', port=self.port)


def init_manager(application, port, extra_directories=()):
    manager = Manager(application)

    manager.add_command('runserver', Server(application, port))

    @manager.command
    def list_routes():
        """List URLs of all application routes."""
        for rule in sorted(manager.app.url_map.iter_rules(), key=lambda r: r.rule):
            print("{:10} {}".format(", ".join(rule.methods - set(['OPTIONS', 'HEAD'])), rule.rule))

    return manager


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
