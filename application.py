#!/usr/bin/env python

import os
from app import create_app
from flask.ext.script import Manager, Shell

application = create_app(os.getenv('FLASH_CONFIG') or 'development')
manager = Manager(application)

if __name__ == '__main__':
	manager.run()

