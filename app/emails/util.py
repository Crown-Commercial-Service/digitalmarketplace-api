from jinja2 import Environment, PackageLoader, select_autoescape
from .markdown_styler import markdown_with_inline_styles
from flask import current_app, url_for
from dmutils.email import send_email, EmailError
import rollbar

DEFAULT_STYLES = {
    'em': '''
        color: #6e6e6e;
        font-style: normal;
    ''',
    'a': '''
        color: #17657a;
        text-decoration: underline;
        font-weight: bold;
    '''
}


template_env = Environment(
    loader=PackageLoader('app.emails', 'templates'),
    autoescape=select_autoescape(['html', 'xml', 'md'])
)


def render_email_template(filename, **kwargs):
    styles = kwargs.pop('styles', DEFAULT_STYLES)

    template = template_env.get_template(filename)
    md = template.render(**kwargs)
    rendered = markdown_with_inline_styles(md, styles)
    template = template_env.get_template('master.html')
    rendered = template.render(body=rendered)
    return rendered


def send_or_handle_error(*args, **kwargs):
    if not current_app.config['SEND_EMAILS']:
        return

    error_desc = kwargs.pop('event_description_for_errors', 'unspecified')

    try:
        result = send_email(*args, **kwargs)
        return result
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
