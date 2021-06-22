#!/usr/bin/env python
"""

Usage:
    fix_application_documents.py <api_endpoint> <api_access_token>
"""
from docopt import docopt
import dmapiclient


def update_application_documents(client, counters, application):
    documents = application.get('documents')

    if not documents:
        print('{}: has no documents'.format(application['id']))
        counters['no_docs'] += 1
        return

    for key in documents.keys():
        documents[key]['application_id'] = application['id']

    try:
        client.req.applications(application['id']).patch(data={'application': {'documents': documents}})
        print('application:{}'.format(application['id']))
        counters['total'] += 1
    except Exception as e:
        print('{}:{}'.format(application['id'], e))
        counters['errors'] += 1


def main(api_url, api_access_token):
    client = dmapiclient.DataAPIClient(api_url, api_access_token)

    counters = {'total': 0, 'no_docs': 0, 'errors': 0}
    applications = client.req.applications().get()
    for application in applications['applications']:
        update_application_documents(client, counters, application)

    for k, v in counters.items():
        print(k, v)


if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
    )
