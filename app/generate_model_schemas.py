#!/usr/bin/env python
import json
from app.models import (
    FrameworkLot, Lot, Framework, ContactInformation, Supplier, SupplierFramework,
    FrameworkAgreement, User, Service, ArchivedService, DraftService, AuditEvent, Brief, BriefUser,
    BriefResponse, BriefClarificationQuestion, DirectAwardProject, DirectAwardProjectUser, DirectAwardSearch,
    DirectAwardSearchResultEntry, Outcome
)

from alchemyjsonschema import SchemaFactory, ForeignKeyWalker


class DMForeignKeyWalker(ForeignKeyWalker):
    """
    Subclassed from https://github.com/podhmo/alchemyjsonschema/blob/master/alchemyjsonschema/__init__.py#L155
    """
    def iterate(self):
        # Tweak this method to handle our underscore-prefixed properties, e.g. Brief._lot_id
        for c in self.mapper.local_table.columns:
            val = self.mapper._props.get(c.name)
            if not val:
                val = self.mapper._props["_" + c.name]
            yield val


fk_factory = SchemaFactory(DMForeignKeyWalker)


# Useful for tests!
def get_models_for_all_db_tables():
    return [
        FrameworkLot, Lot, Framework,
        User, BriefUser, ContactInformation,
        Service, ArchivedService, DraftService, AuditEvent,
        Supplier, SupplierFramework, FrameworkAgreement,
        Brief, BriefResponse, BriefClarificationQuestion,
        DirectAwardProject, DirectAwardProjectUser, DirectAwardSearch, DirectAwardSearchResultEntry, Outcome,
    ]


# These fields will eventually link to framework-specific sub schemas
MODELS_WITH_JSON_FIELDS = {
    ArchivedService: ["data"],
    AuditEvent: ["data"],
    Brief: ["data"],
    BriefResponse: ["data", "award_details"],
    Framework: ["framework_agreement_details"],
    FrameworkAgreement: ["signed_agreement_details", "countersigned_agreement_details"],
    Lot: ["data"],
    DraftService: ["data"],
    Service: ["data"],
    SupplierFramework: ["declaration", "agreed_variations"],
}


# Model property fields, which are prefixed with an underscore on the model (but not in the DB column name)
MAPPED_PROPERTY_FIELDS = [
    '_lot_id',
    '_brief_id'
]


class DMModelSchema:
    """
    Generates a JSON schema for a SQLAlchemy model's database fields
    Skips postgresql.JSON fields on the first parse, and adds them back in afterwards
    Ignores hybrid properties, e.g. 'Brief.status'
    TODO: automate relationships/linked objects (currently added manually)
    TODO: automate real paths to JSON field schemas e.g. 'BriefResponse.award_details' (currently added manually to
        avoid renaming schemas used elsewhere in the code)
    """

    def __init__(self, model):
        self.json_schema = {}
        self.model = model
        self.model_name = model.__tablename__
        self.excludes = MODELS_WITH_JSON_FIELDS.get(model, [])

    def _add_postgres_json_fields(self):
        for field in self.excludes:
            self.json_schema['properties'][field] = {
                "type": "object",
                "properties": {
                    "$ref": "#/path/to/{}_{}/schema".format(self.model_name, field)
                }
            }

    def _add_schema_meta_info(self):
        self.json_schema["$schema"] = "http://json-schema.org/schema#"

    def _remove_mapped_property_fields(self):
        for field in MAPPED_PROPERTY_FIELDS:
            if field in self.json_schema['properties']:
                self.json_schema['properties'].pop(field)
                # If the field is required, replace it with the property
                if field in self.json_schema['required']:
                    self.json_schema['required'].remove(field)
                    self.json_schema['required'].append(field[1:])

    def _parse_model_to_json(self):
        try:
            # SchemaFactory cannot process db.Column(JSON) fields - these are 'added' later
            schema = fk_factory(self.model, excludes=self.excludes)
            self.json_schema = dict(schema.items())
        except KeyError as e:
            # Likely to be a model with a 'mapped' attribute e.g. Brief._lot_id.
            # Add the field to MAPPED_PROPERTY_FIELDS above
            print('Unable to generate schema for {}, Key Error {}'.format(self.model_name, e))
        except Exception as e:
            # Likely to be an unrecognised JSON schema type
            print(e)

    def generate_schema(self):
        self._parse_model_to_json()
        self._add_postgres_json_fields()
        self._remove_mapped_property_fields()
        self._add_schema_meta_info()
        # Return the current schema state for convenience
        return self.json_schema

    def write_schema_to_file(self):
        with open('./json_schemas/model_schemas/{}.json'.format(self.model_name), 'w') as f:
            f.write(json.dumps(self.json_schema, indent=4))


def generate_schemas():
    for m in get_models_for_all_db_tables():
        model_schema = DMModelSchema(m)
        model_schema.generate_schema()
        if model_schema.json_schema:
            model_schema.write_schema_to_file()
        else:
            print("Unable to generate schema for {}".format(model_schema.model_name))
