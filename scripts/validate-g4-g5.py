'''Process G5 JSON export file and validate the services in it

Usage:
    python validate-g5.py <g5_export_file>

Arguments:
    g5_export_file   The file to process

'''

import sys
import json
from jsonschema import validate, ValidationError
from jsonschema.validators import validator_for


with open("../json_schemas/g5-services-schema.json") as json_schema:
    G5_SCHEMA = json.load(json_schema)
    print("Loaded Schema")
    G5_VALIDATOR = validator_for(G5_SCHEMA)
    print("Got validator")
    G5_VALIDATOR.check_schema(G5_SCHEMA)
    print("Checked schema")
    G5_VALIDATOR = G5_VALIDATOR(G5_SCHEMA)
    print("G5 Schema is GO!")

with open("../json_schemas/g4-services-schema.json") as json_schema2:
    G4_SCHEMA = json.load(json_schema2)
    print("Loaded Schema")
    G4_VALIDATOR = validator_for(G4_SCHEMA)
    print("Got validator")
    G4_VALIDATOR.check_schema(G4_SCHEMA)
    print("Checked schema")
    G4_VALIDATOR = G4_VALIDATOR(G4_SCHEMA)
    print("G4 Schema is GO!")


def validate_json(submitted_json):
    if validates_against_schema(G5_VALIDATOR, submitted_json):
        return 'G5 IS GO!'
    elif validates_against_schema(G4_VALIDATOR, submitted_json):
        return 'G4 IS GO!'
    else:
        return reason_for_failure(submitted_json)


def validates_against_schema(validator, submitted_json):
    try:
        validator.validate(submitted_json)
    except ValidationError:
        return False
    else:
        return True


def reason_for_failure(submitted_json):
    response = []
    try:
        validate(submitted_json, G4_SCHEMA)
    except ValidationError as e1:
        response.append('Not G4: %s' % e1.message)

    try:
        validate(submitted_json, G5_SCHEMA)
    except ValidationError as e2:
        response.append('Not G5: %s' % e2.message)

    return '. '.join(response)


def validate_g5_services_file(filename):
    with open(filename) as f:
        data = json.loads(f.read())
        print("processing " + filename)
        for service in data["services"]:
            print("doing " + service["id"])
            print("  ..." + validate_json(service))


def main():
    if len(sys.argv) == 2:
        print("Validating file: '%s'" % sys.argv[-1])
        validate_g5_services_file(sys.argv[-1])
    else:
        print __doc__


if __name__ == '__main__':
    main()
