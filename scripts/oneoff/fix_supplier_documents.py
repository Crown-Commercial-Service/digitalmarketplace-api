#!/usr/bin/env python
"""

Usage:
    fix_supplier_documents.py <api_endpoint> <api_access_token>
"""
from docopt import docopt
import dmapiclient


def update_supplier_documents(client, counters, code):
    applications = client.req.suppliers(code).applications().get()

    if not applications or not applications.get('applications'):
        print('{}: has no applications'.format(code))
        counters['no_app'] += 1
        return

    approved_applications = [a for a in applications['applications'] if a['status'] == 'approved']

    if not approved_applications:
        print('{}: has no approved applications'.format(code))
        counters['not_approved'] += 1
        return

    application = approved_applications[0]
    documents = application.get('documents')

    for key in documents.keys():
        documents[key]['application_id'] = application['id']

    try:
        client.req.suppliers(code).patch(data={'supplier': {'documents': documents}})
        print('supplier:{} application:{}'.format(code, application['id']))
        counters['approved'] += 1
    except Exception as e:
        print('{}:{}'.format(code, e))
        counters['errors'] += 1


def main(api_url, api_access_token):
    client = dmapiclient.DataAPIClient(api_url, api_access_token)

    counters = {'approved': 0, 'no_app': 0, 'errors': 0, 'not_approved': 0}
    suppliers = client.req.suppliers().get(params='per_page=350')
    for supplier in suppliers['suppliers']:
        update_supplier_documents(client, counters, supplier['code'])

    for k, v in counters.items():
        print(k, v)


if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
    )
