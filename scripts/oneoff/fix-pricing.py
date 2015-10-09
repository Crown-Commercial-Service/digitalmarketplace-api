#!/usr/bin/env python
"""Fix G5 and G6 price fields to be strings rather than numbers

Usage:
    fix-pricing.py <api_endpoint> <api_access_token>
"""
from multiprocessing.pool import ThreadPool

from docopt import docopt
from dmutils import apiclient


def update(client):
    def do_update(data):
        i, service = data
        if i % 1000 == 0:
            print(i)
        if service['frameworkSlug'] in ['g-cloud-5', 'g-cloud-6']:
            change = False
            if isinstance(service.get('priceMin'), (int, float)):
                change = True
                service['priceMin'] = '{}'.format(service['priceMin'])
            elif service.get('priceMin') is None:
                change = True
                service['priceMin'] = ''
            if isinstance(service.get('priceMax'), (int, float)):
                change = True
                service['priceMax'] = '{}'.format(service['priceMax'])
            elif service.get('priceMax') is None:
                change = True
                service['priceMax'] = ''
            if change:
                try:
                    client.update_service(service['id'], service, 'migration')
                except apiclient.APIError as e:
                    print(e.message)
                    print(service)
                    pass
    return do_update


def main(api_url, api_access_token):
    client = apiclient.DataAPIClient(api_url, api_access_token)
    pool = ThreadPool(10)
    for i in pool.imap_unordered(update(client), enumerate(client.find_services_iter())):
        pass

if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
    )
