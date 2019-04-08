from jinja2 import Environment, PackageLoader, select_autoescape
from .markdown_styler import markdown_with_inline_styles
from flask import current_app, url_for, abort
from dmutils.email import EmailError
from app.tasks.email import send_email
import six
import rollbar
import re

DEFAULT_STYLES = {
    'em': '''
        color: #6e6e6e;
        font-style: normal;
    ''',
    'a': '''
        color: #17657a;
        text-decoration: underline;
        font-weight: bold;
    ''',
    'blockquote':
    '''
    padding: 2rem; background: #def4f9;
    '''
}


template_env = Environment(
    loader=PackageLoader('app.emails', 'templates'),
    autoescape=select_autoescape(['html', 'xml', 'md'])
)


def fill_template(filename, **kwargs):
    template = template_env.get_template(filename)
    return template.render(**kwargs)


def render_email_template(filename, **kwargs):
    header = kwargs.pop('header', '')
    styles = kwargs.pop('styles', DEFAULT_STYLES)

    md = fill_template(filename, **kwargs)
    rendered = markdown_with_inline_styles(md, styles)
    template = template_env.get_template('master.html')
    rendered = template.render(header=header, body=rendered)
    return rendered


def send_or_handle_error(*args, **kwargs):
    if not current_app.config['SEND_EMAILS']:
        return

    error_desc = kwargs.pop('event_description_for_errors', 'unspecified')

    try:
        send_email.delay(*args, **kwargs)

    except EmailError as e:
        rollbar.report_exc_info()
        current_app.logger.error(
            'email failed to send for event: {}'.format(error_desc),
            'error {error}',
            extra={
                'error': six.text_type(e),
            }
        )
        abort(503, response='Failed to send email for event: {}'.format(error_desc))


def escape_token_markdown(token):
    token = re.sub(r'([_-])', r'\\\1', token)
    return token


def escape_markdown(val):
    val = re.sub(r'([_\-#\[\]\(\)`=>*\\])', r'\\\1', val)
    val = re.sub(r'\s', r' ', val)
    val = re.sub(r'[ ]+', r' ', val)
    return val
