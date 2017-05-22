#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from app import create_app, db
from app.loading import populate_agency_and_council_from_csv_files

from sqlbag import S, load_sql_from_file


port = int(os.getenv('PORT', '5000'))
application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')

dburl = application.config['SQLALCHEMY_DATABASE_URI']

def do_startup():
    with S(dburl) as s:
        populate_agency_and_council_from_csv_files(s)

    with S(dburl) as s:
        load_sql_from_file(s, 'DB/data/on_startup.sql')


do_startup()


if __name__ == '__main__':
    from waitress import serve
    serve(application, port=port, expose_tracebacks=application.config['DEBUG'])
