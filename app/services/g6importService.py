import json
from flask import current_app
from jsonschema import validate

with open("schemata/g6-scs-schema.json") as json_file1:
    SCS_SCHEMA = json.load(json_file1)


def validate_json(submitted_json):
    current_app.logger.info('Validating JSON:' + str(submitted_json))
    try:
        validate(submitted_json, SCS_SCHEMA)
    except:
        return False
    else:
        return True
