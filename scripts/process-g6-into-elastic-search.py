#!/usr/bin/python
'''Process G6 JSON files into elasticsearch

This version reads JSON from disk or DM API and transforms this into the format
expected by the DM search.

Usage:
    process-g6-into-elastic-search.py <es_endpoint> <dir_or_endpoint> [<token>]

Arguments:
    es_endpoint      Full ES index URL
    dir_or_endpoint  Directory path to import or an API URL if token is given
    token            Digital Marketplace API token

'''

import os
import sys
import json
import urllib2

CATEGORY_MAPPINGS = {
    'Accounting and finance': '110',
    'Business intelligence and analytics': '111',
    'Collaboration': '112',
    'Telecoms': '113',
    'Customer relationship management (CRM)': '114',
    'Creative and design': '115',
    'Data management': '116',
    'Sales': '117',
    'Software development tools': '118',
    'Electronic document and records management (EDRM)': '119',
    'Human resources and employee management': '120',
    'IT management': '121',
    'Marketing': '122',
    'Operations management': '123',
    'Project management and planning': '124',
    'Security': '125',
    'Libraries': '126',
    'Schools and education': '127',
    'Energy and environment': '128',
    'Healthcare': '129',
    'Legal': '130',
    'Transport and logistics': '131',
    'Unlisted': '132',
    'Compute': '133',
    'Storage': '134',
    'Other': '135',
    'Platform as a service': '136',
    'Planning': '137',
    'Implementation': '138',
    'Testing': '139',
    'Training': '140',
    'Ongoing support': '141',
    'Specialist Cloud Services': '142'
}


def category_name_to_id(name):
    return CATEGORY_MAPPINGS[name]


def g6_to_g5(data):
    """
    Mappings
        description == serviceSummary
        name == serviceName
        listingId == id
        uniqueName == id
        tags == []
        enable == true
    """

    categories = [category_name_to_id(t) for t in data.get('serviceTypes', [])]
    return {
        'uniqueName': data['id'],
        'tags': data['lot'],
        'name': data['serviceName'],
        'listingId': str(data['id']),
        'description': data['serviceSummary'],
        'enabled': True,
        'expired': False,
        'details': {
            'supplierId': data['supplierId'],
            'lot': data['lot'],
            'categories': categories,
            'features': data['serviceFeatures'],
            'benefits': data['serviceBenefits']
        }
    }


def post_to_es(es_endpoint, data):
    handler = urllib2.HTTPHandler()
    opener = urllib2.build_opener(handler)

    json_data = g6_to_g5(data)

    if not es_endpoint.endswith('/'):
        es_endpoint += '/'
    request = urllib2.Request(es_endpoint + json_data['listingId'],
                              data=json.dumps(json_data))
    request.add_header("Content-Type", 'application/json')

    try:
        opener.open(request)
    except urllib2.HTTPError, error:
        print error


def request_services(endpoint, token):
    handler = urllib2.HTTPBasicAuthHandler()
    opener = urllib2.build_opener(handler)

    page_url = endpoint
    while page_url:
        print "processing page: {}".format(page_url)

        request = urllib2.Request(page_url)
        request.add_header("Authorization", "Bearer {}".format(token))
        response = opener.open(request).read()

        data = json.loads(response)
        for service in data["services"]:
            yield service

        page_url = filter(lambda l: l['rel'] == 'next', data['links'])
        if page_url:
            page_url = page_url[0]['href']


def process_json_files_in_directory(dirname):
    for filename in os.listdir(dirname):
        with open(os.path.join(dirname, filename)) as f:
            data = json.loads(f.read())
            print "doing " + filename
            yield data


def main():
    if len(sys.argv) == 4:
        es_endpoint, endpoint, token = sys.argv[1:]
        for data in request_services(endpoint, token):
            post_to_es(es_endpoint, data)
    elif len(sys.argv) == 3:
        es_endpoint, listing_dir = sys.argv[1:]
        for data in process_json_files_in_directory(listing_dir):
            post_to_es(es_endpoint, data)
    else:
        print __doc__

if __name__ == '__main__':
    main()
