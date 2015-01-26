#!/usr/bin/python
'''Process G6 JSON files into elasticsearch

This version reads JSON from disk and transforms this into the format expected by the DM search

Next steps:
    - needs to be updated to READ from the API and perform the same conversion.
    - needs to be placed into Jenkins and configred to run into live elasticsearch

Usage:
    process-g6-into-elastic-search.py <es_endpoint> <listing_dir_or_api_endpoint>

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
        'details': {
            'supplierId': data['supplierId'],
            'lot': data['lot'],
            'categories': categories
        }
    }


def post_to_es(es_endpoint, index, data):
    handler = urllib2.HTTPHandler()
    opener = urllib2.build_opener(handler)

    json_data = g6_to_g5(data)

    request = urllib2.Request(es_endpoint + json_data['listingId'],
                              data=json.dumps(json_data))
    request.add_header("Content-Type", 'application/json')

    print request.get_full_url()
    print request.get_data()

    try:
        connection = opener.open(request)
    except urllib2.HTTPError, e:
        connection = e
        print connection

    # check. Substitute with appropriate HTTP code.
    if connection.code == 200:
        data = connection.read()
        print str(connection.code) + " " + data
    else:
        print "connection.code = " + str(connection.code)


def request_services(endpoint):
    page_url = endpoint
    while page_url:
        print "requesting {}".format(page_url)
        data = json.loads(urllib2.urlopen(page_url).read())
        for service in data["services"]:
            yield service

        page_url = filter(lambda l: l['rel'] == 'next', data['links'])
        if page_url:
            page_url = page_url[0]


def process_json_files_in_directory(dirname):
    for filename in os.listdir(dirname):
        with open("/Users/martyninglis/g6-final-json/" + filename) as f:
            data = json.loads(f.read())
            print "doing " + filename
            yield data


def main():
    try:
        es_endpoint, listing_dir_or_endpoint = sys.argv[1:]
    except ValueError:
        print __doc__
        return

    if listing_dir_or_endpoint.startswith('http'):
        for data in request_services(listing_dir_or_endpoint):
            post_to_es(es_endpoint, data)
    else:
        for data in process_json_files_in_directory(listing_dir_or_endpoint):
            post_to_es(es_endpoint, data)

if __name__ == '__main__':
    main()
