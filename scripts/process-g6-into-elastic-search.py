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


def attributes(data):
    attributes = []

    #
    # Pricing
    #

    attributes.append(boolean_attribute("freeOption", "q45", data))
    attributes.append(boolean_attribute("trialOption", "q46", data))
    attributes.append(boolean_attribute(
        "educationPricing", "has_education_pricing", data))
    attributes.append(boolean_attribute("terminationCost", "q47", data))

    # Value on G5 has a predixed "/"
    if "minimumContractPeriod" in data:
        attributes.append(
            {"name": "q44", "q44": "/" + data["minimumContractPeriod"]})

    #
    # Technical Information
    #

    # cloud:
    # values in G5 are public | private | hybrid |
    # publicprivate | publichybrid | publicprivatehybrid
    # map G6 to these

    if "cloudDeploymentModel" in data:
        if "Public Cloud" in data["cloudDeploymentModel"]:
            attributes.append({"name": "q18", "q18": "public"})
        if "Private Cloud" in data["cloudDeploymentModel"]:
            attributes.append({"name": "q18", "q18": "private"})
        if "Community Cloud" in data["cloudDeploymentModel"]:
            attributes.append({"name": "q18", "q18": "publicprivatehybrid"})
        if "Hybrid Cloud" in data["cloudDeploymentModel"]:
            attributes.append({"name": "q18", "q18": "hybrid"})

    # Networks:
    # values in G5 are internet | psn | gsi | pnn | n3 | janet | other
    # map G6 to these

    if "networksConnected" in data:
        if "Internet" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "internet"})
        if "Public Services Network (PSN)" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "psn"})
        if "Government Secure intranet (GSi)" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "gsi"})
        if "Police National Network (PNN)" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "pnn"})
        if "New NHS Network (N3)" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "n3"})
        if "Joint Academic Network (JANET)" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "janet"})
        if "Other" in data["networksConnected"]:
            attributes.append({"name": "q19", "q19": "other"})

    attributes.append(boolean_attribute("apiAccess", "q20", data))
    attributes.append(boolean_attribute("openStandardsSupported", "q21", data))
    attributes.append(boolean_attribute("openSource", "q22", data))

    #
    # service management
    #

    # support types is array in G6, boolean in G5 -
    # any G6 value sets G5 to true
    if "supportTypes" in data and len(data["supportTypes"]) > 0:
        attributes.append({"name": "q25", "q25": "true"})

    attributes.append(boolean_attribute("serviceOnboarding", "q26", data))
    attributes.append(boolean_attribute("serviceOffboarding", "q27", data))
    attributes.append(boolean_attribute("dataExtractionRemoval", "q28", data))
    attributes.append(boolean_attribute("datacentresEUCode", "q31", data))
    attributes.append(boolean_attribute("dataBackupRecovery", "q36", data))
    attributes.append(
        boolean_attribute("selfServiceProvisioning", "q39", data))
    attributes.append(boolean_attribute("supportForThirdParties", "q41", data))
    attributes.append(boolean_attribute("supportForThirdParties", "q41", data))

    if "datacentreTier" in data:
        attributes.append({"name": "q32", "q32": data["datacentreTier"]})

    # Data centre tiers:
    # map G6 to these

    if "datacentreTier" in data:
        if "TIA-942 Tier 1" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier1tia942"})
        if "Uptime Institute Tier 1" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier1uptimeinstitute"})
        if "TIA-942 Tier 2" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier2tia942"})
        if "Uptime Institute Tier 2" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier2uptimeinstitute"})
        if "TIA-942 Tier 3" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier3tia942"})
        if "Uptime Institute Tier 3" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier3uptimeinstitute"})
        if "TIA-942 Tier 4" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier4tia942"})
        if "Uptime Institute Tier 4" in data["datacentreTier"]:
            attributes.append({"name": "q32", "q32": "tier4uptimeinstitute"})

    # provising time is 1 Day etc in G6, but
    # the question is "documented?" in G5
    # so any value provokes true
    if "provisioningTime" in data:
        attributes.append({"name": "q40", "q40": "true"})

    #
    # PaaS
    #

    if "lot" in data and data["lot"] == "PaaS":
        # multi selects
        if "guaranteedResources" in data and
        data["guaranteedResources"] is True:
                attributes.append({"name": "lot2q3", "lot2q3": "guaranteed"})
        elif "guaranteedResources" in data and
        data["guaranteedResources"] is False:
                attributes.append({
                    "name": "lot2q3", 
                    "lot2q3": "nonguaranteed"})

        if "persistentStorage" in data and data["persistentStorage"]:
            attributes.append({"name": "lot2q4", "lot2q4": "persistent"})
        elif "persistentStorage" in data and not data["persistentStorage"]:
            attributes.append({"name": "lot2q4", "lot2q4": "nonpersistent"})

        attributes.append(boolean_attribute("elasticCloud", "lot2q2", data))

    #
    # IaaS
    #

    if "lot" in data and data["lot"] is "IaaS":
        # multi selects
        if "guaranteedResources" in data and data["guaranteedResources"]:
            attributes.append({"name": "lot1q3", "lot1q3": "guaranteed"})
        elif "guaranteedResources" in data and not data["guaranteedResources"]:
            attributes.append({"name": "lot1q3", "lot1q3": "nonguaranteed"})

        if "persistentStorage" in data and data["persistentStorage"]:
            attributes.append({"name": "lot1q4", "lot1q4": "persistent"})
        elif "persistentStorage" in data and not data["persistentStorage"]:
            attributes.append({"name": "lot1q4", "lot1q4": "nonpersistent"})

        attributes.append(boolean_attribute("elasticCloud", "lot1q2", data))

    return attributes


def boolean_attribute(g6_field_name, g5_field_name, attributes, data):
    if g6_field_name in data:
        return {
            "name": g5_field_name,
            g5_field_name: str(data[g6_field_name]).lower()
        }


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
        'expired': False,
        'state': 'published',
        'details': {
            'supplierId': data['supplierId'],
            'lot': data['lot'],
            'categories': categories,
            'features': data['serviceFeatures'],
            'benefits': data['serviceBenefits'],
            'attributes': attributes(data)
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
