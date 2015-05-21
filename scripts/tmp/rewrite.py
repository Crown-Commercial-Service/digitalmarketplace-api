import json
import os
import re


def is_enum(pattern):
    return pattern[0] == '^' and pattern[-1] == '$' and '[' not in pattern


def unpack_enum(pattern):
    if '(' not in pattern:
        return [pattern[1:-1]]
    add_empty = False
    if pattern[-2] == '?':
        pattern = pattern[:-1]
        add_empty = True
    parts = pattern[2:-2].split('|')
    # Add empty strings where allowed
    if '' in parts:
        add_empty = True
        parts = filter(None, parts)

    if add_empty:
        parts = [''] + parts
    return parts


def match_pattern(pattern):
    return r'"type": "string",\s+"pattern": "{}"'.format(re.escape(pattern))


def fix_field(raw_data, value):
    """Detect enums and replace them in the raw JSON to avoid reordering"""
    if 'pattern' in value and is_enum(value['pattern']):
        enum_json = json.dumps(unpack_enum(value['pattern']))
        raw_data = re.sub(match_pattern(value['pattern']),
                          '"enum": {}'.format(enum_json),
                          raw_data,
                          flags=re.DOTALL)
    return raw_data


def fix_properties(raw_data, properties):
    for key, value in properties.items():
        raw_data = fix_field(raw_data, value)
        if 'oneOf' in value:
            for item in value['oneOf']:
                if 'items' in item:
                    raw_data = fix_field(raw_data, item['items'])
        elif 'items' in value:
            raw_data = fix_field(raw_data, value['items'])
        elif 'properties' in value:
            raw_data = fix_properties(raw_data, value['properties'])
    return raw_data


for filename in os.listdir('json_schemas'):
    if not filename.endswith('.json'):
        continue
    path = os.path.join('json_schemas', filename)
    with open(path) as f:
        raw_data = f.read()
        data = json.loads(raw_data)
    print(path)
    raw_data = fix_properties(raw_data, data['properties'])
    with open(path, 'w') as f:
        f.write(raw_data)
