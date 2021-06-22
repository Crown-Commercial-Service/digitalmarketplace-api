#!/usr/bin/env python
"""Fix G5 and G6 price fields to be strings rather than numbers

Usage:
    fix-pricing.py <api_endpoint> <api_access_token>
"""
from multiprocessing.pool import ThreadPool

from docopt import docopt
import dmapiclient


def update(client):
    def do_update(data):
        i, service = data
        if i % 1000 == 0:
            print(i)
        update = {}
        if service['frameworkSlug'] in ['g-cloud-5', 'g-cloud-6']:
            change = False
            if isinstance(service.get('priceMin'), (int, float)):
                change = True
                update['priceMin'] = '{}'.format(service['priceMin'])
            elif service.get('priceMin') is None:
                change = True
                update['priceMin'] = ''
            if isinstance(service.get('priceMax'), (int, float)):
                change = True
                update['priceMax'] = '{}'.format(service['priceMax'])
            elif service.get('priceMax') is None:
                change = True
                update['priceMax'] = ''
            if change:
                try:
                    client.update_service(service['id'], update, 'migration')
                    return 1
                except dmapiclient.APIError as e:
                    print(str(e))
                    print(service)
                    pass
        return 0
    return do_update


def main(api_url, api_access_token):
    client = dmapiclient.DataAPIClient(api_url, api_access_token)
    pool = ThreadPool(10)
    count = 1
    for i in pool.imap_unordered(update(client), enumerate(client.find_services_iter())):
        count += i
        if count % 1000 == 0:
            print("** {}".format(count))

if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
    )
