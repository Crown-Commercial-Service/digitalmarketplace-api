import paramiko
from sshtunnel import SSHTunnelForwarder

import json
import io
import os
import sys
from base64 import b64decode

from sqlbag import S, load_sql_from_file, temporary_database as temporary_db, sql_from_folder, raw_execute, DB_ERROR_TUPLE
from migra import Migration
from contextlib import contextmanager
import tempfile
import shutil
import subprocess


from migrations import load_from_app_model


PENDING_FOLDER = 'DB/migration/pending'
DRY_RUN = False


@contextmanager
def tempfolder():
    t = None
    try:
        t = tempfile.mkdtemp()
        yield t
    finally:
        if t:
            shutil.rmtree(t)


def databases_are_equal(dburl_a, dburl_b):
    with S(dburl_a) as s0, S(dburl_b) as s1:
        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()

        if m.statements:
            print('DIFFERENCES FOUND:')
            print(m.sql)
        return not m.statements


def do_schema_dump(dburl, outfile):
    COMMAND = 'pg_dump --no-owner --no-privileges --schema-only --column-inserts -f {} {}'

    command = COMMAND.format(outfile, dburl)

    print('MAKING DUMP OF SCHEMA: '.format(command))
    subprocess.check_output(command, shell=True)
    print('DUMP COMPLETE')


def do_migration(REAL_DB_URL):
    PENDING = sql_from_folder(PENDING_FOLDER)

    with tempfolder() as tempf:
        outfile = os.path.join(tempf, 'schemadump.sql')
        do_schema_dump(REAL_DB_URL, outfile)

        for i in range(len(PENDING) + 1):
            ATTEMPTING = list(reversed(PENDING))[:i]
            ATTEMPTING.reverse()

            print("TESTING MIGRATION USING LAST {} MIGRATION FILES".format(i))

            with temporary_db() as dummy_db_url, temporary_db() as target_db_url:
                with S(dummy_db_url) as s_dummy:
                    load_sql_from_file(s_dummy, outfile)

                    try:
                        for migration_sql in ATTEMPTING:
                            raw_execute(s_dummy, migration_sql)
                    except DB_ERROR_TUPLE as e:
                        print('TRIED USING LAST {} PENDING FILES TO MIGRATE BUT THIS FAILED, MOVING TO NEXT'.format(i))
                        continue

                load_from_app_model(target_db_url)

                if databases_are_equal(dummy_db_url, target_db_url):
                    print('APPLYING LAST {} PENDING FILES'.format(i))

                    with S(REAL_DB_URL) as s_real:
                        for migration_sql in ATTEMPTING:
                            if not DRY_RUN:
                                print("EXECUTING:")
                                print(migration_sql)
                                raw_execute(s_real, migration_sql)
                            else:
                                print('DRY RUN, would apply:')
                                print(migration_sql)
                    print('SUCCESS: DATABASE UP TO DATE.')
                    return 0
                else:
                    print('TRIED USING LAST {} PENDING FILES TO MIGRATE BUT THIS DOES NOT GIVE A CORRECT OUTCOME, MOVING TO NEXT'.format(i))

        print('COULD NOT FIND A CORRECT MIGRATION PATH :(')
        return 1


@contextmanager
def connection_from_encoded_config(encoded_config):
    CONFIG = json.loads(b64decode(encoded_config))

    pk = paramiko.RSAKey.from_private_key(file_obj=io.StringIO(CONFIG['private_key']))

    with SSHTunnelForwarder(
        (CONFIG['remote_host'], 22),
        ssh_username=CONFIG['user'],
        ssh_pkey=pk,
        remote_bind_address=(CONFIG['private_host'], 5432),
        local_bind_address=('0.0.0.0', CONFIG['local_port'])
    ):
        yield CONFIG['connection_url']


def main(task_method, encoded_config):
    with connection_from_encoded_config(encoded_config) as REAL_DB_URL:
        result = task_method(REAL_DB_URL)
    return result

if __name__ == '__main__':
    _, task_method_name, encoded_config = sys.argv

    try:
        task_method = getattr(sys.modules[__name__], task_method_name)
    except AttributeError:
        print('no such task')
        sys.exit(1)

    result = main(task_method, encoded_config)
    sys.exit(result)