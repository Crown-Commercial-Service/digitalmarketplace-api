"""

Usage:
    scripts/generate_lots_export_for_ccs_sourcing.py <data_api_url> <data_api_token>

Example:
    ./generate_lots_export_for_ccs_sourcing.py http://api myToken
"""
import csv
import sys
from itertools import groupby
from operator import itemgetter
from docopt import docopt
from dmutils.apiclient import DataAPIClient, HTTPError

def aggregate(drafts):
    """
    Process a list of drafts
    - only process G7 drafts
    - only process drafts with a service name as aborted copies are drafts
        with no service but are NOT on supplier dashboards
    - Group by lot
    - Then Group by status
    Returns a map keyed by lot.
    - Each map entry is the count of drafts in each status
    :param drafts: List of drafts services JSON objects
    :return: Map of lot to status counts
    """
    result = {}
    g7_drafts = sorted(
        [g7 for g7 in drafts if g7['frameworkSlug'] == 'g-cloud-7' and 'serviceName' in g7],
        key=lambda draft_to_sort: draft_to_sort['lot']
    )

    drafts_by_lot = groupby(g7_drafts, itemgetter('lot'))

    for lot, draft in drafts_by_lot:
        drafts_by_status_and_lot = groupby(draft, itemgetter('status'))
        status_counts = {}
        for status, drafts in drafts_by_status_and_lot:
            status_counts[status] = len(list(drafts))
        result[lot] = status_counts
    return result

def headers():
    """
    Generate the headers for the CSV file
    :return array of strings representing headers:
    """
    csv_headers = list()
    csv_headers.append('Digital Marketplace ID')
    csv_headers.append('Digital Marketplace Name')
    csv_headers.append('Digital Marketplace Duns number')
    csv_headers.append('IaaS: Complete')
    csv_headers.append('IaaS: Incomplete')
    csv_headers.append('PaaS: Complete')
    csv_headers.append('PaaS: Incomplete')
    csv_headers.append('SaaS: Complete')
    csv_headers.append('SaaS: Incomplete')
    csv_headers.append('SCS: Complete')
    csv_headers.append('SCS: Incomplete')
    return csv_headers

def submitted_count(drafts):
    """
    Get count of submitted services
    Defaults to 0 if no submitted services
    :param drafts:
    :return:
    """
    return drafts.get('submitted', 0)

def not_submitted_count(drafts):
    """
    Get count of not-submitted services
    Defaults to 0 if no not-submitted services
    :param drafts:
    :return:
    """
    return drafts.get('not-submitted', 0)

def suppliers_lot_count(data_api_url, data_api_token):
    """
    Generate the CSV
    - takes the data api details
    - iterates through all suppliers
    - foreach supplier hits the draft API to recover the services
    - builds CSV row for each supplier
    :param data_api_url:
    :param data_api_token:
    :return:
    """
    client = DataAPIClient(data_api_url, data_api_token)

    writer = csv.writer(sys.stdout, delimiter=',', quotechar='"')
    writer.writerow(headers())

    for supplier in client.find_suppliers_iter():
        try:
            drafts = list()
            for draft_service in client.find_draft_services_iter(supplier['id']):
                drafts.append(draft_service)

            if drafts:
                aggregations = aggregate(drafts)
                supplier_row = list()
                supplier_row.append(supplier['id'])
                supplier_row.append(supplier['name'])
                supplier_row.append(supplier.get('dunsNumber', ""))
                supplier_row.append(submitted_count(aggregations.get('IaaS', {})))
                supplier_row.append(not_submitted_count(aggregations.get('IaaS', {})))
                supplier_row.append(submitted_count(aggregations.get('PaaS', {})))
                supplier_row.append(not_submitted_count(aggregations.get('PaaS', {})))
                supplier_row.append(submitted_count(aggregations.get('SaaS', {})))
                supplier_row.append(not_submitted_count(aggregations.get('SaaS', {})))
                supplier_row.append(submitted_count(aggregations.get('SCS', {})))
                supplier_row.append(not_submitted_count(aggregations.get('SCS', {})))
                writer.writerow(supplier_row)
        except HTTPError as e:
            if e.status_code == 404:
                # not all suppliers make a declaration so this is fine
                pass
            else:
                raise e

if __name__ == '__main__':
    arguments = docopt(__doc__)

    suppliers_lot_count(
        data_api_url=arguments['<data_api_url>'],
        data_api_token=arguments['<data_api_token>']
    )
