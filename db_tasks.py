import json
import os
import sys
from base64 import b64decode
import http.client
import ssl
import urllib.parse
import base64

from sqlbag import S, load_sql_from_file, temporary_database as temporary_db, sql_from_folder, raw_execute, DB_ERROR_TUPLE
from migra import Migration
from contextlib import contextmanager
import tempfile
import shutil
import pickle
import subprocess

from migrations import load_from_app_model


PENDING_FOLDER = 'DB/migration/pending'
SHELF_PATH = 'DB/migration/'
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


def shelf_full_path(filename):
    return os.path.join(SHELF_PATH, filename)


def shelve_result(filename, result):
    shelf_path = shelf_full_path(filename)

    with open(shelf_path, "wb") as shelf_file:
        pickle.dump(result, shelf_file)


def get_shelved_result(filename):
    shelf_path = shelf_full_path(filename)
    if not (os.access(shelf_path, os.R_OK)):
        raise Exception('Migration test results not found.')

    with open(shelf_path, "rb") as shelf_file:
        result = pickle.load(shelf_file)

    return result


def databases_are_equal(dburl_a, dburl_b):
    with S(dburl_a) as s0, S(dburl_b) as s1:
        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()

        if m.statements:
            print('DIFFERENCES FOUND:')
            print(m.sql)
        return not m.statements


def remove_search_path(outfile):
    print('REMOVING SEARCH PATH FROM SCHEMA')
    with open(outfile, 'r') as schema_file:
        lines = schema_file.readlines()

    with open(outfile, 'w') as schema_file:
        for line in lines:
            if line != 'SELECT pg_catalog.set_config(\'search_path\', \'\', false);\n':
                schema_file.write(line)


# cld_host: uaa.system.example.com
# dbexport_host: db-export.system.example.com
def do_schema_dump(outfile, cld_host, dbexport_host, username, password, service_binding):
    ctx = ssl.create_default_context()
    auth_str = "%s:%s" % ("db-export-tool-api", "notasecret")
    print('GETTING TOKEN')
    conn = http.client.HTTPSConnection(cld_host, 443, context=ctx)
    conn.request("POST", "/oauth/token", urllib.parse.urlencode({
        "grant_type": "password",
        "scope": ",".join(["openid", "cloud_controller.read"]),
        "username": username,
        "password": password,
    }), {
        "Authorization": "Basic %s" % base64.b64encode(auth_str.encode('utf-8')).decode('ascii'),
        "Content-Type": "application/x-www-form-urlencoded",
    })
    resp = conn.getresponse()
    if resp.status != 200:
        raise Exception('Could not get token from {}'.format(cld_host))
    token = json.loads(resp.read())["access_token"]
    conn.close()

    print('DOWNLOADING SCHEMA')
    conn = http.client.HTTPSConnection(dbexport_host, 443, context=ctx)
    conn.request("GET", "/dbSchema?%s" % urllib.parse.urlencode({
        "servicebinding": service_binding,
    }), None, {
        "Authorization": "Bearer %s" % token,
    })

    resp = conn.getresponse()
    if resp.status != 200:
        raise Exception('Could not get schema from {}'.format(dbexport_host))
    schema = resp.read()
    conn.close()

    with open(outfile, "wb") as schema_file:
        schema_file.write(schema)

    remove_search_path(outfile)

# cfapi_host: api.system.example.com
# service_name: database name (must be at least one app already deployed that is bound to it)
def v2_test_migration(shelf_filename, cfapi_host, username, password, service_name):
    cld_host = '.'.join(['uaa'] + cfapi_host.split('.')[1:])
    dbexport_host = '.'.join(['db-export'] + cfapi_host.split('.')[1:])

    service_guid = subprocess.check_output(['cf', 'service', service_name, '--guid']).strip().decode()
    if not len(service_guid):
        raise ValueError("service_guid returned empty")

    response = json.loads(subprocess.check_output(['cf', 'curl', '/v2/service_instances/%s/service_bindings' % service_guid]))
    service_binding = response["resources"][0]["metadata"]["guid"]

    return test_migration(shelf_filename, cld_host, dbexport_host, username, password, service_binding)

# cld_host: uaa.system.example.com
# dbexport_host: db-export.system.example.com
def test_migration(shelf_filename, cld_host, dbexport_host, username, password, service_binding):
    PENDING = sql_from_folder(PENDING_FOLDER)

    with tempfolder() as tempf:
        outfile = os.path.join(tempf, 'schemadump.sql')
        do_schema_dump(outfile, cld_host, dbexport_host, username, password, service_binding)

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
                    except DB_ERROR_TUPLE:
                        print('TRIED USING LAST {} PENDING FILES TO MIGRATE BUT THIS FAILED, MOVING TO NEXT'.format(i))
                        continue

                load_from_app_model(target_db_url)

                if databases_are_equal(dummy_db_url, target_db_url):
                    print('SUCCESS WITH LAST {} PENDING FILES'.format(i))
                    shelve_result(shelf_filename, ATTEMPTING)
                    return 0
                else:
                    print('TRIED USING LAST {} PENDING FILES TO MIGRATE BUT THIS DOES NOT GIVE A CORRECT OUTCOME, MOVING TO NEXT'.format(i))

        print('COULD NOT FIND A CORRECT MIGRATION PATH :(')
        return 1


def do_migration(shelf_filename):
    REAL_DB_URL = os.environ['DATABASE_URL'].replace('reconnect=true', '')

    ATTEMPTING = get_shelved_result(shelf_filename)

    print('APPLYING PENDING FILE')

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


def main(task_method, args):
    return task_method(*args)


if __name__ == '__main__':
    try:
        task_method = getattr(sys.modules[__name__], sys.argv[1])
    except AttributeError:
        print('no such task')
        sys.exit(1)

    result = main(task_method, sys.argv[2:])
    sys.exit(result)
