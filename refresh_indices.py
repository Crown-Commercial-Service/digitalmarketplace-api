#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from dmutils import init_manager
from flask.ext.migrate import Migrate, MigrateCommand

from app import create_app, db

port = int(os.getenv('PORT', '5000'))
application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')

with application.app_context():
    from app.search_indices import delete_indices, create_indices
    delete_indices()
    create_indices()
