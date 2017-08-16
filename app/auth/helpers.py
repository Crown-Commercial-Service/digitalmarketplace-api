import requests
from dmutils.email import (
    decode_token, EmailError, generate_token, InvalidToken, ONE_DAY_IN_SECONDS, send_email
)
from flask import current_app, render_template_string
import rollbar


def generate_creation_token(name, email_address, user_type, **unused):
    data = {
        'name': name,
        'email_address': email_address,
        'user_type': user_type
    }
    token = generate_token(data, current_app.config['SECRET_KEY'], current_app.config['SIGNUP_INVITATION_TOKEN_SALT'])
    return token


def decode_creation_token(token):
    try:
        data = decode_token(
            token,
            current_app.config['SECRET_KEY'],
            current_app.config['SIGNUP_INVITATION_TOKEN_SALT'],
            14 * ONE_DAY_IN_SECONDS
        )
    except InvalidToken:
        return InvalidToken

    if not set(('name', 'email_address')).issubset(set(data.keys())):
        raise InvalidToken

    return data


_GOV_EMAIL_DOMAINS = [
    'gov.au',
    'abc.net.au',
    'melbournewater.com.au',
    'tourism.australia.com',
    'victrack.com.au',
    'auspost.com.au',
    'mav.asn.au',
    'healthdirect.org.au',
    'unitywater.com'
]

_GOV_EMAILS = [
    'itprocurement@unsw.edu.au',
    'bill.simpson-young@data61.csiro.au'
]


def is_government_email(email_address):
    domain = email_address.split('@')[-1]
    return any(email_address in _GOV_EMAILS or domain == d or domain.endswith('.' + d) for d in _GOV_EMAIL_DOMAINS)


def slack_escape(text):
    """
    Escapes special characters for Slack API.

    https://api.slack.com/docs/message-formatting#how_to_escape_characters
    """
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def notify_team(subject, body, more_info_url=None):
    """
    Generic routine for making simple notifications to the Marketplace team.

    Notification messages should be very simple so that they're compatible with a variety of backends.
    """
    # ensure strings can be encoded as ascii only
    body = body.encode("ascii", "ignore").decode('ascii')
    subject = subject.encode("ascii", "ignore").decode('ascii')

    if current_app.config.get('DM_TEAM_SLACK_WEBHOOK', None):
        slack_body = slack_escape(body)
        if more_info_url:
            slack_body += '\n' + more_info_url
        data = {
            'attachments': [{
                'title': subject,
                'text': slack_body,
                'fallback': '{} - {} {}'.format(subject, body, more_info_url),
            }],
            'username': 'Marketplace Notifications',
        }
        response = requests.post(
            current_app.config['DM_TEAM_SLACK_WEBHOOK'],
            json=data
        )
        if response.status_code != 200:
            msg = 'Failed to send notification to Slack channel: {} - {}'.format(response.status_code, response.text)
            current_app.logger.error(msg)

    if current_app.config.get('DM_TEAM_EMAIL', None):
        email_body = render_template_string(
            '<p>{{ body }}</p>{% if more_info_url %}<a href="{{ more_info_url }}">More info</a>{% endif %}',
            body=body, more_info_url=more_info_url
        )
        try:
            send_email(
                current_app.config['DM_TEAM_EMAIL'],
                email_body,
                subject,
                current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
                current_app.config['DM_GENERIC_ADMIN_NAME'],
            )
        except EmailError as error:
            try:
                msg = error.message
            except AttributeError:
                msg = str(error)
            rollbar.report_exc_info()
            current_app.logger.error('Failed to send notification email: {}'.format(msg))
