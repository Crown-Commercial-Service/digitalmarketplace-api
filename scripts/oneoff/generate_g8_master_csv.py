"""
Generate a CSV (to stdout) with per-lot draft statistics for each supplier

Usage:
    scripts/oneoff/generate_g8_master_csv.py <data_api_url> <data_api_token>

Example:
    scripts/oneoff/generate_g8_master_csv.py http://api myToken
"""
import csv
from sys import stdout
from itertools import product, chain
from collections import Counter, OrderedDict

from docopt import docopt
from dmapiclient import DataAPIClient

_lot_slug_status_label = lambda lot_slug, status: "{}_{}".format(lot_slug, status)


def generate_g8_master_csv(
        data_api_url,
        data_api_token,
        outfile=stdout,
        target_framework_slug="g-cloud-8",
        target_statuses_labels=OrderedDict((
            ("submitted", "completed",),
            ("not-submitted", "draft",),
        )),
        target_lot_slugs=("saas", "paas", "iaas", "scs",),
        ):
    client = DataAPIClient(data_api_url, data_api_token)

    writer = csv.DictWriter(outfile, lineterminator="\n", fieldnames=(
        "supplier_id",
        "supplier_name",
        "application_status",
        "declaration_status",
        ) + tuple(_lot_slug_status_label(status, lot_slug) for status, lot_slug in product(
            target_statuses_labels.values(), target_lot_slugs))
    )
    writer.writeheader()

    # we iterate over each user but only need to emit each supplier once
    seen_suppliers = set()

    for user in client.export_users(target_framework_slug)["users"]:
        if user["supplier_id"] not in seen_suppliers:
            supplier_lot_statuses = Counter()
            for draft in client.find_draft_services_iter(user["supplier_id"], framework=target_framework_slug):
                if draft["status"] in target_statuses_labels and draft["lot"] in target_lot_slugs:
                    label = _lot_slug_status_label(target_statuses_labels[draft["status"]], draft["lot"])
                    supplier_lot_statuses[label] += 1

            writer.writerow({k: unicode(v).encode("utf-8") for k, v in chain(
                # these values can just be passed through from the user object
                ((k, user[k]) for k in ("supplier_id", "application_status", "declaration_status",)),
                # these values require an api fetch
                (
                    ("supplier_name", client.get_supplier(user["supplier_id"])["suppliers"]["name"],),
                ),
                # these values can be patched on from the stat counter
                supplier_lot_statuses.items(),
            )})
            seen_suppliers.add(user["supplier_id"])

if __name__ == "__main__":
    arguments = docopt(__doc__)
    generate_g8_master_csv(
        data_api_url=arguments['<data_api_url>'],
        data_api_token=arguments['<data_api_token>'],
    )
