import json
import jsonschema
from flask import current_app
from jsonschema import validate

with open("schemata/g6-scs-schema.json") as json_file1:
    G6_SCS_SCHEMA = json.load(json_file1)

with open("schemata/g6-saas-schema.json") as json_file2:
    G6_SAAS_SCHEMA = json.load(json_file2)

with open("schemata/g6-iaas-schema.json") as json_file3:
    G6_IAAS_SCHEMA = json.load(json_file3)

with open("schemata/g6-paas-schema.json") as json_file4:
    G6_PAAS_SCHEMA = json.load(json_file4)

    
def validate_json(submitted_json):
    #current_app.logger.info('Validating JSON:' + str(submitted_json))
    try:
        validate(submitted_json, G6_SCS_SCHEMA)
        return 'G6-SCS'
    except jsonschema.ValidationError as e1:
        try:
            validate(submitted_json, G6_SAAS_SCHEMA)
            return 'G6-SaaS'
        except jsonschema.ValidationError as e2:
            try:
                validate(submitted_json, G6_IAAS_SCHEMA)
                return 'G6-IaaS'
            except jsonschema.ValidationError as e3:
                try:
                    validate(submitted_json, G6_PAAS_SCHEMA)
                    return 'G6-PaaS'
                except jsonschema.ValidationError as e4:
                    print e4.message
                    print 'Failed validation'
                    return False
    else:
        return True
