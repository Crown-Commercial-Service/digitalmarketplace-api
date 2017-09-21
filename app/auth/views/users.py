from app.auth.user import create_user
from flask import jsonify, current_app
from flask_login import current_user, login_required, logout_user, login_user
from sqlalchemy.exc import InvalidRequestError, IntegrityError
from urllib import quote
from app import db, encryption
from app.auth import auth
from app.auth.helpers import (
    generate_reset_password_token, decode_reset_password_token
)
from app.models import Application, User, Supplier
from app.utils import get_json_from_request, json_has_required_keys
from app.emails.users import (
    send_account_activation_email, send_account_activation_manager_email, send_new_user_onboarding_email,
    send_reset_password_confirm_email
)
from dmutils.csrf import get_csrf_token
from dmutils.email import EmailError, InvalidToken
from app.auth.helpers import decode_creation_token, is_government_email
from app.auth.applications import create_application
from app.auth.user import is_duplicate_user, update_user_details
from app.auth.suppliers import get_supplier
from datetime import datetime


@auth.route('/ping', methods=["GET"])
def ping():
    try:
        user_type = current_user.role
    except AttributeError:
        user_type = 'anonymous'

    try:
        supplier_code = current_user.supplier_code
    except AttributeError:
        supplier_code = None

    return jsonify(
        isAuthenticated=current_user.is_authenticated,
        userType=user_type,
        supplierCode=supplier_code,
        csrfToken=get_csrf_token()
    )


@auth.route('/_protected', methods=["GET"])
@login_required
def protected():
    return jsonify(data='protected')


@auth.route('/_post', methods=["POST"])
def post():
    return jsonify(data='post')


@auth.route('/login', methods=['POST'])
def login():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["emailAddress", "password"])
    email_address = json_payload.get('emailAddress', None)
    user = User.get_by_email_address(email_address.lower())

    if user is None or (user.supplier and user.supplier.status == 'deleted'):
        return jsonify(message='User does not exist'), 403
    elif encryption.authenticate_user(json_payload.get('password', None), user) and user.active:
        user.logged_in_at = datetime.utcnow()
        user.failed_login_count = 0
        db.session.add(user)
        db.session.commit()

        login_user(user)

        return jsonify(
            isAuthenticated=user.is_authenticated,
            userType=user.role,
            csrfToken=get_csrf_token()
        )
    else:
        user.failed_login_count += 1
        db.session.add(user)
        db.session.commit()

        return jsonify(message="Could not authorize user"), 403


@auth.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return jsonify(message='The user was logged out successfully'), 200


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


@auth.route('/create-user', methods=['POST'])
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


@auth.route('/reset-password/', methods=['POST'])
def send_reset_password_email():
    json_payload = get_json_from_request()
    email_address = json_payload.get('email_address', None)
    if email_address is None:
        return jsonify(message='One or more required args were missing from the request'), 400

    user = User.query.filter(
        User.email_address == email_address).first()

    try:
        reset_password_token = generate_reset_password_token(
            email_address,
            user.id,
        )

        reset_password_url = '{}{}/reset-password/{}'.format(
            current_app.config['FRONTEND_ADDRESS'],
            current_app.config['REACT_APP_ROOT'],
            quote(reset_password_token)
        )

        send_reset_password_confirm_email(
            email_address=email_address,
            url=reset_password_url,
            locked=user.locked
        )

    except Exception as error:
        return jsonify(message=error.message), 400

    return jsonify(
        email_address=email_address,
        token=reset_password_token
    ), 200


@auth.route('/reset-password/<string:token>', methods=['GET'])
def get_reset_user(token):
    try:
        data = decode_reset_password_token(token.encode())

    except InvalidToken as error:
        return jsonify(message=error.message), 400

    return jsonify(
        token=token,
        email_address=data.get('email_address', None),
        user_id=data.get('user_id', None)
    ), 200


@auth.route('/reset-password/<string:token>', methods=['POST'])
def reset_password(token):
    json_payload = get_json_from_request()

    required_keys = ['password', 'confirmPassword', 'email_address', 'user_id']

    if not set(required_keys).issubset(json_payload):
        return jsonify(message='One or more required args were missing from the request'), 400

    if json_payload['password'] != json_payload['confirmPassword']:
        return jsonify(message="Passwords do not match"), 400

    data = decode_reset_password_token(token.encode())

    if data.get('error', None) is not None:
        return jsonify(message="An error occured decoding the reset password token"), 400

    try:
        update_user_details(
            password=json_payload['password'],
            email_address=json_payload['email_address'],
            user_id=json_payload['user_id']
        )

        return jsonify(
            message="User with email {}, successfully updated their password".format(json_payload['email_address']),
            email_address=json_payload['email_address']
        ), 200

    except Exception as error:
        return jsonify(message=error.message), 400


@auth.route('/profile', methods=['GET'])
@login_required
def get_user_profile():
    user = {'email': current_user.email_address, 'role': current_user.role}
    if current_user.supplier_code is not None:
        supplier = get_supplier(current_user.supplier_code)
        user['supplier'] = supplier

    return jsonify(user=user), 200
