from user import create_user
from flask import jsonify
from flask_login import current_user, login_required, logout_user
from sqlalchemy.exc import DataError, InvalidRequestError, IntegrityError
from app.auth import auth
from app.models import User, Application
from app.utils import get_json_from_request
from app.emails.users import (
    send_account_activation_email, send_account_activation_manager_email, send_new_user_onboarding_email
)
from dmapiclient import HTTPError
from dmutils.csrf import get_csrf_token
from dmutils.email import EmailError, InvalidToken
from helpers import decode_creation_token, is_government_email
from applications import create_application
from user import is_duplicate_user


@auth.route('/ping', methods=["GET"])
def ping():
    try:
        user_type = current_user.role
    except AttributeError:
        user_type = 'anonymous'

    return jsonify(
        isAuthenticated=current_user.is_authenticated,
        userType=user_type,
        csrfToken=get_csrf_token()
    )


@auth.route('/_protected', methods=["GET"])
@login_required
def protected():
    return jsonify(data='protected')


@auth.route('/_post', methods=["POST"])
def post():
    return jsonify(data='post')


@auth.route('/signup', methods=['POST'])
def send_signup_email():
    try:
        json_payload = get_json_from_request()
        json_payload['name'] and json_payload['email_address'] and json_payload['user_type']
        if json_payload['user_type'] == 'buyer':
            json_payload['employment_status']

        name = json_payload.get('name', None)
        email_address = json_payload.get('email_address', None)
        user_type = json_payload.get('user_type', None)
        employment_status = json_payload.get('employment_status', None)
        line_manager_name = json_payload.get('line_manager_name', None)
        line_manager_email = json_payload.get('line_manager_email', None)

    except KeyError:
        return jsonify(message='One or more required args were missing from the request'), 400

    user = User.query.filter(
        User.email_address == email_address.lower()).first()

    if user is not None:
        return jsonify(
            email_address=email_address,
            message="A user with the email address '{}' already exists".format(email_address)
        ), 409

    if user_type == 'seller' or user_type == 'applicant':
        if is_duplicate_user(email_address):
            return jsonify(
                email_address=email_address,
                message='An account with this email domain already exists'
            ), 409

    if user_type == 'buyer' and not is_government_email(email_address):
        return jsonify(
            email_address=email_address,
            message="A buyer account must have a valid government entity email domain"
        ), 400

    if employment_status == 'contractor':
        try:
            send_account_activation_manager_email(
                manager_name=line_manager_name,
                manager_email=line_manager_email,
                applicant_name=name,
                applicant_email=email_address
            )
            return jsonify(
                email_address=email_address,
                message="Email invite sent successfully"
            ), 200

        except EmailError:
            return jsonify(message='An error occured when trying to send an email'), 500

    if employment_status == 'employee' or user_type == 'seller':
        try:
            send_account_activation_email(
                name=name,
                email_address=email_address,
                user_type=user_type
            )
            return jsonify(
                email_address=email_address,
                message="Email invite sent successfully"
            ), 200

        except EmailError:
            return jsonify(
                email_address=email_address,
                message='An error occured when trying to send an email'
            ), 500

    else:
        return jsonify(
            email_address=email_address,
            message='An error occured when trying to send an email'
        ), 400


@auth.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return jsonify(message='The user was logged out successfully'), 200


@auth.route('/signup/validate-invite/<string:token>', methods=['GET'])
def validate_invite_token(token):
    try:
        data = decode_creation_token(token.encode())
        return jsonify(data)

    except InvalidToken:
        return jsonify(message='The token provided is invalid. It may have expired'), 400

    except TypeError:
        return jsonify(
            message='The invite token passed to the server is not a recognizable token format'
        ), 400


@auth.route('/createuser', methods=['POST'])
def submit_create_account():
    json_payload = get_json_from_request()
    required_keys = ['name', 'email_address', 'password', 'user_type']
    if not set(required_keys).issubset(json_payload):
        return jsonify(message='One or more required args were missing from the request'), 400

    user_type = json_payload.get('user_type')
    name = json_payload.get('name')
    email_address = json_payload.get('email_address')
    shared_application_id = json_payload.get('application_id', None)

    user = User.query.filter(
        User.email_address == email_address.lower()).first()

    if user is not None:
        return jsonify(
            application_id=user.application_id,
            message="A user with the email address '{}' already exists".format(email_address)
        ), 409

    if user_type == "seller":
        if shared_application_id is None:
            try:
                application = create_application(email_address=email_address, name=name)
                json_payload['application_id'] = application.id

            except InvalidRequestError:
                return jsonify(message="An application with this email address already exists"), 409

            except IntegrityError:
                return jsonify(message="An application with this email address already exists"), 409

        else:
            application = Application.query.filter(
                Application.id == shared_application_id).first()

            if not application:
                return jsonify(message='An invalid application id was passed to create new user api'), 400
            else:
                # TODO: associate new user with existing application
                pass

    try:
        user = create_user(data=json_payload)

        send_new_user_onboarding_email(
            name=user.name,
            email_address=user.email_address,
            user_type=user_type
        )

        user = {
            k: v for k, v in user._dict.items() if k in [
                'name', 'email_address', 'application_id', 'role', 'supplier_code']
        }

        return jsonify(user)

    except IntegrityError as error:
        return jsonify(message=error.message), 409

    except Exception as error:
        return jsonify(message=error.message), 400
