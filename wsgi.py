#!/usr/bin/env python

import os

from app import create_app
from sqlbag import S, load_sql_from_file


port = int(os.getenv('PORT', '5000'))
application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')

dburl = application.config['SQLALCHEMY_DATABASE_URI']


def do_startup():
    with S(dburl) as s:
        load_sql_from_file(s, 'DB/data/on_startup.sql')


do_startup()


if __name__ == '__main__':
    from waitress import serve
    serve(application, port=port, expose_tracebacks=application.config['DEBUG'])
