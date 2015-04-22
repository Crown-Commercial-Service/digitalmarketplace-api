from __future__ import absolute_import
import logging
import uuid

from flask import g, request
from flask.ctx import has_app_context

LOG_FORMAT = '%(asctime)s %(app_name)s %(levelname)s %(request_id)s: ' \
             '%(message)s [in %(pathname)s:%(lineno)d]'


def init_app(app):
    app.config.setdefault('DM_LOG_LEVEL', 'INFO')
    app.config.setdefault('DM_APP_NAME', 'none')
    app.config.setdefault('DM_LOG_PATH', './log/application.log')
    app.config.setdefault('DM_REQUEST_ID_HEADER', 'DM-Request-ID')
    app.config.setdefault('DM_DOWNSTREAM_REQUEST_ID_HEADER', '')

    handler = get_handler(app)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.getLevelName(app.config['DM_LOG_LEVEL']))

    request_id_header = app.config['DM_REQUEST_ID_HEADER']
    downstream_header = app.config['DM_DOWNSTREAM_REQUEST_ID_HEADER']

    @app.before_request
    def before_request():
        g.request_id = get_request_id(request,
                                      request_id_header, downstream_header)

    @app.after_request
    def after_request(response):
        response.headers[request_id_header] = g.request_id
        return response


def get_handler(app):
    formatter = CustomFormatter(LOG_FORMAT, app.config['DM_APP_NAME'])

    handler = logging.FileHandler(app.config['DM_LOG_PATH'])
    handler.setLevel(logging.getLevelName(app.config['DM_LOG_LEVEL']))
    handler.setFormatter(formatter)

    return handler


def get_request_id(request, request_id_header, downstream_header):
    if request_id_header in request.headers:
        return request.headers.get(request_id_header)
    elif downstream_header and downstream_header in request.headers:
        return request.headers.get(downstream_header)
    else:
        return str(uuid.uuid4())


class CustomFormatter(logging.Formatter):
    def __init__(self, log_format, app_name):
        super(CustomFormatter, self).__init__(log_format,
                                              '%Y-%m-%dT%H:%M:%S')
        self.app_name = app_name

    def _get_request_id(self):
        if not has_app_context():
            return 'not-in-request'
        elif not hasattr(g, 'request_id'):
            return 'no-request-id'
        else:
            return g.request_id

    def _build_record(self, record):
        record.app_name = self.app_name
        record.request_id = self._get_request_id()

        return record

    def format(self, record):
        return super(CustomFormatter, self).format(self._build_record(record))
