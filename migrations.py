from __future__ import print_function, unicode_literals

import six

import sys
import io
import os

from migra import Migration

from sqlbag import S, temporary_database as temporary_db, load_sql_from_file, load_sql_from_folder


from config import configs

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
import subprocess


from app import models  # noqa
from app import create_app, db


if six.PY2:
    input = raw_input


def prompt(question):
    print(question + ' ', end='')
    return input().strip().lower() == 'y'


def load_current_production_state(dburl):
    with S(dburl) as s:
        load_sql_from_file(s, 'DB/dumps/prod.schema.dump.sql')


def load_current_staging_state(dburl):
    with S(dburl) as s:
        load_sql_from_file(s, 'DB/dumps/staging.schema.dump.sql')


def load_post_migration_state(dburl):
    load_current_production_state(dburl)

    with S(dburl) as s:
        load_sql_from_folder(s, 'DB/migration/pending')


def load_from_app_model(dburl):
    with S(dburl) as s:
        db.metadata.create_all(s.bind.engine)
        load_sql_from_file(s, 'DB/migration/setup.sql')


def load_test_fixtures(dburl):
    with S(dburl) as s:
        load_sql_from_file(s, 'DB/data/test_fixtures.sql')


def sync():
    DB_URL = get_current_app_db_url()

    with temporary_db() as TEMP_DB_URL:
        load_from_app_model(TEMP_DB_URL)

        with S(DB_URL) as s_current, S(TEMP_DB_URL) as s_target:
            m = Migration(s_current, s_target)
            m.set_safety(False)
            m.add_all_changes()

            if m.statements:
                print('THE FOLLOWING CHANGES ARE PENDING:', end='\n\n')
                print(m.sql)

                if prompt('Apply these changes?'):
                    print('Applying...')
                    m.apply()
                else:
                    print('Not applying.')
            else:
                print('Already synced.')


def pending(write_to_file=False):
    with temporary_db() as CURRENT_DB_URL, temporary_db() as TARGET_DB_URL:
        load_current_production_state(CURRENT_DB_URL)
        load_from_app_model(TARGET_DB_URL)

        with S(CURRENT_DB_URL) as s_current, S(TARGET_DB_URL) as s_target:
            m = Migration(s_current, s_target)

            m.set_safety(False)
            m.add_all_changes()

            print('Pending:\n{}'.format(m.sql))

            if write_to_file:
                with io.open('DB/migration/pending/pending.sql', 'w') as w:
                    w.write(m.sql)


def check_migration_result():
    with temporary_db() as CURRENT_DB_URL, temporary_db() as TARGET_DB_URL:
        load_post_migration_state(CURRENT_DB_URL)
        load_from_app_model(TARGET_DB_URL)

        with S(CURRENT_DB_URL) as s_current, S(TARGET_DB_URL) as s_target:
            m = Migration(s_current, s_target)

            m.set_safety(False)
            m.add_all_changes()

            print('Differences:\n{}'.format(m.sql))


def staging_vs_app():
    with temporary_db() as CURRENT_DB_URL, temporary_db() as TARGET_DB_URL:
        load_current_staging_state(CURRENT_DB_URL)
        load_from_app_model(TARGET_DB_URL)

        with S(CURRENT_DB_URL) as s_current, S(TARGET_DB_URL) as s_target:
            m = Migration(s_current, s_target)

            m.set_safety(False)
            m.add_all_changes()

            print('Differences:\n{}'.format(m.sql))


def staging_vs_prod():
    with temporary_db() as CURRENT_DB_URL, temporary_db() as TARGET_DB_URL:
        load_current_staging_state(CURRENT_DB_URL)
        load_current_production_state(TARGET_DB_URL)

        with S(CURRENT_DB_URL) as s_current, S(TARGET_DB_URL) as s_target:
            m = Migration(s_current, s_target)

            m.set_safety(False)
            m.add_all_changes()

            print('Differences:\n{}'.format(m.sql))


def prod_vs_app():
    with temporary_db() as CURRENT_DB_URL, temporary_db() as TARGET_DB_URL:
        load_current_production_state(CURRENT_DB_URL)
        load_from_app_model(TARGET_DB_URL)

        with S(CURRENT_DB_URL) as s_current, S(TARGET_DB_URL) as s_target:
            m = Migration(s_current, s_target)

            m.set_safety(False)
            m.add_all_changes()

            print('Differences:\n{}'.format(m.sql))


def staging_errors():
    with temporary_db() as CURRENT_DB_URL, temporary_db() as TARGET_DB_URL:
        load_current_staging_state(CURRENT_DB_URL)
        load_current_production_state(TARGET_DB_URL)

        with S(CURRENT_DB_URL) as s_current, S(TARGET_DB_URL) as s_target:
            m = Migration(s_current, s_target)

            m.set_safety(False)
            m.add_all_changes()

            print('Differences:\n{}'.format(m.sql))


def get_current_app_db_url():
    app = create_app(os.getenv('DM_ENVIRONMENT') or 'development')
    return app.config['SQLALCHEMY_DATABASE_URI']


if __name__ == '__main__':
    try:
        task_method = getattr(sys.modules[__name__], sys.argv[1])
    except AttributeError:
        print('no such task')
        sys.exit(1)

    task_method(*sys.argv[2:])
