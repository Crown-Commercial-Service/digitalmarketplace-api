#!/usr/bin/python

import os
import json 
import urllib
import urllib2

'''
Script to process G6 JSON files into elasticsearch

- this version reads JSON from disk and transforms this into the format expected by the DM search
- Next steps:
	- needs to be updated to READ from the API and perform the same conversion.
	- needs to be placed into Jenkins and configred to run into live elasticsearch

'''

## Mappings
#// description == serviceSummary
#// name == serviceName
#// listingId == id
#// uniqueName == id
#// tags == []
#// enable == true

## globals
suppliers = {}	
ccs_suppliers = {}
server = "http://localhost:9200"

category_mappings = {	
	'Accounting and finance' : '110',
	'Business intelligence and analytics' : '111',
	'Collaboration' : '112', 
	'Telecoms' : '113',
	'Customer relationship management (CRM)' : '114', 
	'Creative and design' : '115', 
	'Data management' : '116', 
	'Sales' : '117', 
	'Software development tools' : '118', 
	'Electronic document and records management (EDRM)' : '119',
	'Human resources and employee management' : '120',
	'IT management' : '121', 
	'Marketing' : '122', 
	'Operations management' : '123', 
	'Project management and planning' : '124',
	'Security' : '125',
	'Libraries' : '126',
	'Schools and education' : '127',
	'Energy and environment' : '128', 
	'Healthcare' : '129', 
	'Legal' : '130', 
	'Transport and logistics' : '131', 
	'Unlisted' : '132', 
	'Compute' : '133', 
	'Storage': '134', 
	'Other' : '135', 
	'Platform as a service' : '136', 
	'Planning' : '137', 
	'Implementation' : '138', 
	'Testing' : '139', 
	'Training' : '140', 
	'Ongoing support' : '141', 
	'Specialist Cloud Services' : '142' 
}

def map_category_name_to_id(name):
	return category_mappings[name]

def post_to_es(data):
	listingId = str(data['id'])
	name = data['serviceName']
	description = data['serviceSummary']
	uniqueName = data['id']
	supplierId = data['supplierId']
	categories = []
	lot = data['lot']
	method = "POST"
	handler = urllib2.HTTPHandler()
	opener = urllib2.build_opener(handler)

	if 'serviceTypes' in data:
		for t in data['serviceTypes']:
			categories.append(map_category_name_to_id(t))
	

	json_data =  json.dumps({
		'uniqueName' : uniqueName, 
		'tags' : data['lot'],
		'name' :  name,
		'listingId' : listingId, 
		'description' : description, 
		'enabled' : True, 
		'details' : {
			'supplierId' : supplierId, 
			'lot': lot, 
			'categories' : categories
		}
	})

	print json_data

	request = urllib2.Request(server + "/uk.gov.cabinetoffice.digital.gdm/listing/" + str(listingId), data=json_data)
	request.add_header("Content-Type",'application/json')
	request.get_method = lambda: method

	print request.get_full_url()
	print request.get_data()

	try:
		connection = opener.open(request)
	except urllib2.HTTPError,e:
		connection = e
		print connection

	# check. Substitute with appropriate HTTP code.
	if connection.code == 200:
		data = connection.read()
		print str(connection.code)  + " " + data
	else:
		print "connection.code = " +  str(connection.code)

def process_json_in_directories():
	for filename in os.listdir("/Users/martyninglis/g6-final-json/"):
		file = open("/Users/martyninglis/g6-final-json/" + filename)
		data = json.loads(file.read())
		print "doing " + filename
		post_to_es(data)
		file.close()


## process json files
process_json_in_directories()





