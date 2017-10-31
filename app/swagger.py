from flask import abort, make_response, jsonify
from flasgger import Swagger

SWAGGER_TEMPLATE = {
    'info': {
        'title': 'Digital Marketplace API'
    },
    'securityDefinitions': {'basicAuth': {'type': 'basic'}}
}

SWAGGER_CONFIG = {
    'headers': [
    ],
    'specs': [
        {
            'endpoint': 'apispec_1',
            'route': '/api/apispec_1.json',
            'rule_filter': lambda rule: True,  # all in
            'model_filter': lambda tag: True,  # all in
        }
    ],
    'static_url_path': '/api/flasgger_static',
    'swagger_ui': True,
    'specs_route': '/api/apidocs/'
}


def validation_error_handler(err, data, schema):
    error = str(err)
    if '\n' in error:
        error = error.split('\n')[0]

    abort(make_response(jsonify(message=error), 400))


swag = Swagger(config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE, validation_error_handler=validation_error_handler)
