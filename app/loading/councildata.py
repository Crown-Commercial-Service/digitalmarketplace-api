
import re
from sqlbag import S, temporary_database
from csvx import OrderedDictReader


UPSERT_STATEMENT = """
    insert into {tablename}
    as t ({columnlist})
    values ({valuelist})
    on conflict ({unique_columns})
    do update set
        {upserts}
"""


def camel_to_lower(name):
    if ' ' in name:
        name = name.lower().replace(' ', '_')
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    camel = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return camel


def fix_camels(d):
    return {camel_to_lower(k): v for k, v in d.items()}


def upsert_statement(item, tablename, unique_columns):
    columnlist = ', '.join(item.keys())
    valuelist = ', '.join(':{}'.format(k) for k in item.keys())

    unique_columns = ', '.join(unique_columns)
    upserts = ', '.join(['{} = excluded.{}'.format(_, _) for _ in item.keys()])

    return UPSERT_STATEMENT.format(
        tablename=tablename,
        columnlist=columnlist,
        valuelist=valuelist,
        unique_columns=unique_columns,
        upserts=upserts
    )


def populate_agency_and_council_from_csv_files(s):
    TNAMES = ['agency', 'council']

    for t in TNAMES:
        with OrderedDictReader('data/emaildomains-{}.csv'.format(t)) as csvrows:
            for item in csvrows:
                item = fix_camels(item)

                if t == 'council':
                    if item['home_page']:
                        item['home_page'] = item['home_page'].rstrip('/')
                        item['domain'] = item['home_page'].split('://')[-1].lstrip('www.')
                    else:
                        continue

                if t == 'agency':
                    del item['acronym_in_header']
                    item['name'] = item['agency_name']
                    del item['agency_name']
                    item['domain'] = item['email_domain']
                    del item['email_domain']

                upsert = upsert_statement(item, t, ['domain'])
                s.execute(upsert, item)
