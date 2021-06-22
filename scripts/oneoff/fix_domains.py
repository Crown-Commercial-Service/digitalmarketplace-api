# This script may produce duplicates as multiple legacy domains map to a single new domain.
#
# Generate legacy supplier domain list:
# copy (select distinct price_schedule.supplier_id, substring(service_role.name, position(' ' in service_role.name))
# from price_schedule inner join service_role on service_role.id = price_schedule.service_role_id
# order by price_schedule.supplier_id) To '/tmp/service_roles.csv' With CSV;
#
# Generate domain list:
# copy (select * from domain) to '/tmp/domains.csv' with csv;
#
import csv
import io
import yaml


def upsert(table, **kwargs):
    """ update/insert rows into objects table (update if the row already exists)
        given the key-value pairs in kwargs """
    keys = ["%s" % k for k in kwargs]
    values = ["'%s'" % v for v in kwargs.values()]
    sql = list()
    sql.append("INSERT INTO %s (" % table)
    sql.append(", ".join(keys))
    sql.append(") VALUES (")
    sql.append(", ".join(values))
    sql.append(");\n")
    return "".join(sql)


def main(service_roles_file, domains_file, domain_mapping_file):
    with io.open(domain_mapping_file) as f:
        DOMAIN_MAPPING = yaml.load(f.read())

    DOMAINS = {}
    with open(domains_file) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            DOMAINS[row[1]] = row[0]

    STATEMENTS = []
    with open(service_roles_file) as csvfile:
        reader = csv.reader(csvfile)
        with open('/tmp/domain_updates.sql', 'w') as update_file:
            for row in reader:
                statement = upsert('supplier_domain', supplier_id=row[0],
                                   domain_id=DOMAINS[DOMAIN_MAPPING[row[1].strip()]], status='assessed')
                if statement not in STATEMENTS:
                    STATEMENTS.append(statement)
                    update_file.write(statement)
                    print(statement)


if __name__ == "__main__":
    service_roles_file = '/tmp/service_roles.csv'
    domains_file = '/tmp/domains.csv'
    domain_mapping_file = '../../data/domain_mapping_old_to_new.yaml'
    main(service_roles_file, domains_file, domain_mapping_file)
