import builtins
import mock

from app.generate_model_schemas import generate_schemas, DMModelSchema, get_models_for_all_db_tables
from app.models import Brief, BriefClarificationQuestion


def test_generate_schema():
    # Brief has a JSON field 'data' and a mapped property '_lot_id'
    schema = DMModelSchema(Brief)
    assert schema.generate_schema() == {
        "$schema": "http://json-schema.org/schema#",
        "title": "Brief",
        "type": "object",
        "properties": {
            "id": {
                "type": "integer"
            },
            "framework_id": {
                "type": "integer"
            },
            "lot_id": {
                "type": "integer"
            },
            "is_a_copy": {
                "type": "boolean"
            },
            "created_at": {
                "type": "string",
                "format": "date-time"
            },
            "updated_at": {
                "type": "string",
                "format": "date-time"
            },
            "published_at": {
                "type": "string",
                "format": "date-time"
            },
            "withdrawn_at": {
                "type": "string",
                "format": "date-time"
            },
            "cancelled_at": {
                "type": "string",
                "format": "date-time"
            },
            "unsuccessful_at": {
                "type": "string",
                "format": "date-time"
            },
            "data": {
                "type": "object",
                "properties": {
                    "$ref": "#/path/to/briefs_data/schema"
                }
            }
        },
        "required": [
            "id",
            "framework_id",
            "is_a_copy",
            "lot_id"
        ]
    }


@mock.patch.object(builtins, 'open')
def test_write_schema_to_file(m_open):
    model = BriefClarificationQuestion
    schema = DMModelSchema(model)
    schema.generate_schema()
    schema.write_schema_to_file()
    assert m_open.call_args_list == [
        mock.call('./json_schemas/model_schemas/brief_clarification_questions.json', 'w')
    ]


@mock.patch.object(builtins, 'open')
def test_write_all_models_to_files(m_open):
    generate_schemas()
    assert len(m_open.call_args_list) == len(get_models_for_all_db_tables())
