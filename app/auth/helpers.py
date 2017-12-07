from flask import current_app, render_template_string, jsonify, make_response, abort as flask_abort
import requests
import rollbar
from app.models import User
from dmutils.email import (
    decode_token, EmailError, generate_token, InvalidToken, ONE_DAY_IN_SECONDS, send_email,
    parse_fernet_timestamp
)
from functools import wraps
from flask_login import current_user
import pendulum
from dmutils.csrf import get_csrf_token


def role_required(*roles):
    def role_decorator(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not any(current_user.has_role(role) for role in roles):
                return jsonify(message="One of [{}] roles required".format(", ".join(roles))), 403
            return func(*args, **kwargs)

        return decorated_view

    return role_decorator


def is_current_supplier(func):
    @wraps(func)
    def decorated_view(code, *args, **kwargs):
        if current_user.role == 'supplier' and current_user.supplier_code != code:
            return jsonify(message="Unauthorised to view supplier"), 403
        return func(code, *args, **kwargs)
    return decorated_view


def generate_creation_token(name, email_address, user_type, framework, **unused):
    data = {
        'name': name,
        'email_address': email_address,
        'user_type': user_type,
        'framework': framework
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


def user_info(user):
    try:
        user_type = current_user.role
    except AttributeError:
        user_type = 'anonymous'

    try:
        email_address = current_user.email_address
    except AttributeError:
        email_address = None

    try:
        supplier_code = current_user.supplier_code
    except AttributeError:
        supplier_code = None

    try:
        framework = current_user.frameworks[0].framework.slug if current_user.frameworks else 'digital-marketplace'
    except AttributeError:
        framework = None

    try:
        is_authenticated = current_user.is_authenticated
    except AttributeError:
        is_authenticated = False

    return {
        "isAuthenticated": is_authenticated,
        "userType": user_type,
        "supplierCode": supplier_code,
        "emailAddress": email_address,
        "csrfToken": get_csrf_token(),
        "framework": framework
    }


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


def generate_reset_password_token(email_address, user_id):
    data = {"user_id": user_id, "email_address": email_address}
    token = generate_token(
        data,
        current_app.config['SECRET_KEY'],
        current_app.config['RESET_PASSWORD_SALT']
    )

    return token


def decode_reset_password_token(token):
    data = decode_token(
        token,
        current_app.config['SECRET_KEY'],
        current_app.config['RESET_PASSWORD_SALT'],
        1 * ONE_DAY_IN_SECONDS
    )
    timestamp = parse_fernet_timestamp(token)

    email_address = data.get('email_address', None)

    if email_address is None:
        raise ValueError("Required argument email address was not returned from token decoding")

    user = User.query.filter(
        User.email_address == email_address).first()
    user_last_changed_password_at = user.password_changed_at

    """
        timestamp of token returned from parse_fernet_timestamp does not use ms,
        User model does so if you compare
        these two immediately - like you will in a test, this will return a false positive
    """
    if timestamp < user_last_changed_password_at.replace(microsecond=0):
        current_app.logger.info("Token generated earlier than password was last changed")
        raise InvalidToken("Token generated earlier than password was last changed")

    return data


def get_root_url(framework_slug):
    return current_app.config['APP_ROOT'].get(framework_slug)


def abort(message):
    return flask_abort(make_response(jsonify(message=message), 400))


def parse_date(dt):
    try:
        return pendulum.parse(dt).date()
    except ValueError, e:
        abort(message=str(e))


class ServiceException(Exception):
    def __init__(self, msg):
        self.msg = msg


class Service(object):
    __model__ = None

    def all(self):
        return self.__model__.query.all()

    def get(self, id):
        return self.__model__.query.get(id)
