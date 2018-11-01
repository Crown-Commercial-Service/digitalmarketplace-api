from app.api.user import create_user
from flask import jsonify, current_app, request
from flask_login import current_user, login_required, logout_user, login_user
from urllib import quote
from app import db, encryption
from app.api import api
from app.api.helpers import (
    generate_reset_password_token, decode_reset_password_token, get_root_url,
    get_email_domain
)
from app.models import User, has_whitelisted_email_domain
from app.utils import get_json_from_request
from app.emails.users import (
    send_account_activation_email, send_account_activation_manager_email,
    send_reset_password_confirm_email, orams_send_account_activation_admin_email,
    send_user_existing_password_reset_email
)
from dmutils.email import EmailError, InvalidToken
from app.api.helpers import decode_creation_token, user_info
from app.api.user import is_duplicate_user, update_user_details
from datetime import datetime
from app.swagger import swag


@api.route('/users/me', methods=["GET"], endpoint='ping')
def me():
    """Current user
    ---
    tags:
      - users
    definitions:
      UserInfo:
        type: object
        properties:
          isAuthenticated:
            type: boolean
          userType:
            type: string
          supplierCode:
            type: integer
          csrfToken:
            type: string
    responses:
      200:
        description: User
        schema:
          $ref: '#/definitions/UserInfo'

    """
    return jsonify(user_info(current_user))


# deprecated
@api.route('/ping', methods=["GET"])
def me_deprecated():
    return jsonify(user_info(current_user))


@api.route('/_protected', methods=["GET"])
@login_required
def protected():
    return jsonify(data='protected')


@api.route('/_post', methods=["POST"])
def post():
    return jsonify(data='post')


@api.route('/login', methods=['POST'])
@swag.validate('LoginUser')
def login():
    """Login user
    ---
    tags:
      - auth
    security:
      - basicAuth: []
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: LoginUser
          required:
            - emailAddress
            - password
          properties:
            emailAddress:
              type: string
            password:
              type: string
    responses:
      200:
        description: User
        schema:
          $ref: '#/definitions/UserInfo'
    """
    json_payload = request.get_json()
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

        return jsonify(user_info(user))
    else:
        user.failed_login_count += 1
        db.session.add(user)
        db.session.commit()

        return jsonify(message="Could not authorize user"), 403


@api.route('/logout', methods=['GET'])
@login_required
def logout():
    """Logout user
    ---
    tags:
      - auth
    security:
      - basicAuth: []
    responses:
      200:
        description: Message
        type: object
        properties:
          message:
            type: string
    """
    logout_user()
    return jsonify(message='The user was logged out successfully'), 200


@api.route('/signup', methods=['POST'])
@swag.validate('SignupUser')
def signup():
    """Signup user
    ---
    tags:
      - auth
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: SignupUser
          required:
            - name
            - email_address
            - user_type
          properties:
            name:
              type: string
            email_address:
              type: string
            user_type:
              type: string
            employment_status:
              type: string
            line_manager_name:
              type: string
            line_manager_email:
              type: string
            framework:
              type: string
    responses:
      200:
        description: User
        schema:
          $ref: '#/definitions/UserInfo'
    """
    json_payload = request.get_json()
    name = json_payload.get('name', None)
    email_address = json_payload.get('email_address', None)
    user_type = json_payload.get('user_type', None)
    employment_status = json_payload.get('employment_status', None)
    line_manager_name = json_payload.get('line_manager_name', None)
    line_manager_email = json_payload.get('line_manager_email', None)
    framework = json_payload.get('framework', 'digital-marketplace')

    user = User.query.filter(
        User.email_address == email_address.lower()).first()

    if user is not None:
        send_user_existing_password_reset_email(user.name, email_address)
        return jsonify(
            email_address=email_address,
            message="Email invite sent successfully"
        ), 200

    if user_type == 'seller' or user_type == 'applicant':
        if is_duplicate_user(email_address):
            return jsonify(
                email_address=email_address,
                message='An account with this email domain already exists'
            ), 409

    # New ORAMS users don't need their email domain checked as that's done manually
    if framework == 'orams':
        try:
            orams_send_account_activation_admin_email(name, email_address, framework)
            return jsonify(
                email_address=email_address,
                message="Email invite sent successfully"
            ), 200

        except EmailError:
            return jsonify(message='An error occured when trying to send an email'), 500

    if user_type == 'buyer' and not has_whitelisted_email_domain(get_email_domain(email_address)):
        return jsonify(
            email_address=email_address,
            message="A buyer account must have a valid government entity email domain"
        ), 403

    if employment_status == 'contractor':
        try:
            send_account_activation_manager_email(
                manager_name=line_manager_name,
                manager_email=line_manager_email,
                applicant_name=name,
                applicant_email=email_address,
                framework=framework
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
                user_type=user_type,
                framework=framework
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


@api.route('/send-invite/<string:token>', methods=['POST'])
def send_invite(token):
    """Send invite
    ---
    tags:
      - auth
    consumes:
      - application/json
    parameters:
      - name: token
        in: path
        type: string
        required: true
        default: all
    responses:
      200:
        description: Email address
        type: object
        properties:
          email_address:
            type: string
          name:
            type: string
    """
    try:
        data = decode_creation_token(token.encode())
        email_address = data.get('email_address', None)
        name = data.get('name', None)
        framework = data.get('framework', 'digital-marketplace')
        user_type = data.get('user_type', None)
        send_account_activation_email(name, email_address, user_type, framework)
        return jsonify(email_address=email_address, name=name), 200
    except InvalidToken:
        return jsonify(message='An error occured when trying to send an email'), 400


@api.route('/users', methods=['POST'], endpoint='create_user')
@swag.validate('AddUser')
def add():
    """Add user
    ---
    tags:
      - users
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: AddUser
          required:
            - name
            - email_address
            - user_type
            - password
          properties:
            name:
              type: string
            email_address:
              type: string
            password:
              type: string
            user_type:
              type: string
            framework:
              type: string
            shared_application_id:
              type: string
    responses:
      200:
        description: User
        type: object
        properties:
          role:
            type: string
          email_address:
            type: string
          name:
            type: string
          supplier_code:
            type: string
          application_id:
            type: string
    """
    return create_user()


# deprecated
@api.route('/create-user', methods=['POST'])
@swag.validate('AddUser')
def add_deprecated():
    return create_user()


@api.route('/reset-password/framework/<string:framework_slug>', methods=['POST'])
def send_reset_password_email(framework_slug):
    json_payload = get_json_from_request()
    email_address = json_payload.get('email_address', None)
    if email_address is None:
        return jsonify(message='One or more required args were missing from the request'), 400
    user = User.query.filter(
        User.email_address == email_address).first()

    if user is None:
        return jsonify(email_address=email_address), 200

    app_root_url = get_root_url(framework_slug)

    try:
        reset_password_token = generate_reset_password_token(
            email_address,
            user.id
        )

        reset_password_url = '{}{}/reset-password/{}'.format(
            current_app.config['FRONTEND_ADDRESS'],
            app_root_url,
            quote(reset_password_token)
        )

        send_reset_password_confirm_email(
            email_address=email_address,
            url=reset_password_url,
            locked=user.locked,
            framework=framework_slug
        )

    except Exception as error:
        return jsonify(message=error.message), 400

    return jsonify(
        email_address=email_address,
        token=reset_password_token
    ), 200


@api.route('/reset-password/<string:token>', methods=['GET'])
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


@api.route('/reset-password/<string:token>', methods=['POST'])
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
            user_id=json_payload['user_id']
        )

        return jsonify(
            message="User with email {}, successfully updated their password".format(json_payload['email_address']),
            email_address=json_payload['email_address']
        ), 200

    except Exception as error:
        return jsonify(message=error.message), 400
