from datetime import datetime
from urllib import quote, unquote_plus

from flask import current_app, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app import db, encryption
from app.api import api
from app.api.business import team_business
from app.api.helpers import (allow_api_key_auth, get_email_domain,
                             get_root_url, role_required, user_info)
from app.api.services import (agency_service, api_key_service,
                              key_values_service, user_claims_service)
from app.api.user import create_user, is_duplicate_user, update_user_details
from app.emails.users import (send_account_activation_email,
                              send_account_activation_manager_email,
                              send_reset_password_confirm_email,
                              send_user_existing_password_reset_email)
from app.models import User, has_whitelisted_email_domain
from app.swagger import swag
from app.tasks import publish_tasks
from app.utils import get_json_from_request
from dmutils.email import EmailError, InvalidToken


@api.route('/users/me', methods=["GET"], endpoint='ping')
def me():
    return jsonify(user_info(current_user))


# deprecated
@api.route('/ping', methods=["GET"])
@allow_api_key_auth
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

    if user_type == 'buyer' and not has_whitelisted_email_domain(get_email_domain(email_address)):
        return jsonify(
            email_address=email_address,
            message="A buyer account must have a valid government entity email domain"
        ), 403

    user_data = {
        'name': name,
        'user_type': user_type,
        'framework': framework,
        'employment_status': employment_status
    }
    claim = user_claims_service.make_claim(type='signup', email_address=email_address, data=user_data)
    if not claim:
        return jsonify(message="There was an issue completing the signup process."), 500

    publish_tasks.user_claim.delay(
        publish_tasks.compress_user_claim(claim),
        'created'
    )

    if employment_status == 'contractor':
        try:
            send_account_activation_manager_email(
                token=claim.token,
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
                token=claim.token,
                email_address=email_address,
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
@role_required('admin')
def send_invite(token):
    """Send invite
    ---
    tags:
      - auth
    consumes:
      - application/json
    parameters:
      - name: e
        in: query
        type: string
        required: true
        description: URL encoded email address
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
    email_address_encoded = request.args.get('e') or ''
    if not email_address_encoded:
        return jsonify(message='You must provide an email address when validating a new account'), 400
    email_address = unquote_plus(email_address_encoded)
    claim = user_claims_service.find(type='signup', token=token, email_address=email_address,
                                     claimed=False).one_or_none()
    if not claim:
        return jsonify(message='Invalid token'), 400
    name = claim.data.get('name', None)
    framework = claim.data.get('framework', 'digital-marketplace')
    user_type = claim.data.get('user_type', None)
    send_account_activation_email(token, email_address, framework)
    return jsonify(email_address=email_address, name=name), 200


@api.route('/create-user/<string:token>', methods=['POST'], endpoint='create_user')
def add(token):
    """Creates a new user based on the token claim and email address provided.
    ---
    tags:
      - users
    consumes:
      - application/json
    parameters:
      - name: e
        in: query
        type: string
        required: true
        description: URL encoded email address
      - name: token
        in: path
        type: string
        required: true
        description: the validation token
      - name: body
        in: body
        required: true
        schema:
          required:
            - password
          properties:
            password:
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
    email_address_encoded = request.args.get('e') or ''
    if not email_address_encoded:
        return jsonify(message='You must provide an email address when validating a new account'), 400
    email_address = unquote_plus(email_address_encoded)
    json_payload = request.get_json()
    password = json_payload.get('password', None)
    if not password:
        return jsonify(message='You must provide a password for your new user account'), 400
    claim = user_claims_service.find(type='signup', token=token, email_address=email_address,
                                     claimed=False).one_or_none()
    if not claim:
        return jsonify(message='Invalid token'), 400
    user = create_user(
        user_type=claim.data['user_type'],
        name=claim.data['name'],
        email_address=email_address,
        password=password,
        framework=claim.data['framework'],
        supplier_code=claim.data.get('supplier_code', None)
    )
    try:
        claim = user_claims_service.validate_and_update_claim(type='signup', token=token, email_address=email_address)
        if not claim:
            return jsonify(message='Invalid token'), 400
    except Exception as error:
        return jsonify(message='Invalid token'), 400

    publish_tasks.user_claim.delay(
        publish_tasks.compress_user_claim(claim),
        'updated'
    )

    return user


@api.route('/reset-password', methods=['POST'])
def send_reset_password_email():
    json_payload = get_json_from_request()
    email_address = json_payload.get('email_address', None)
    framework_slug = json_payload.get('framework', None)
    if email_address is None:
        return jsonify(message='One or more required args were missing from the request'), 400
    user = User.query.filter(
        User.email_address == email_address.lower()).first()

    if user is None:
        return jsonify(email_address=email_address), 200

    app_root_url = get_root_url(framework_slug)

    try:
        user_data = {
            'user_id': user.id
        }
        claim = user_claims_service.make_claim(type='password_reset', email_address=email_address, data=user_data)
        if not claim:
            return jsonify(message="There was an issue completing the password reset process."), 500

        publish_tasks.user_claim.delay(
            publish_tasks.compress_user_claim(claim),
            'created'
        )

        send_reset_password_confirm_email(
            token=claim.token,
            email_address=email_address,
            locked=user.locked,
            framework=framework_slug
        )

    except Exception as error:
        return jsonify(message=error.message), 400

    return jsonify(
        email_address=email_address
    ), 200


@api.route('/reset-password/<string:token>', methods=['POST'])
def reset_password(token):
    email_address_encoded = request.args.get('e') or ''
    if not email_address_encoded:
        return jsonify(message='You must provide an email address when resetting a password'), 400
    email_address = unquote_plus(email_address_encoded)

    json_payload = get_json_from_request()

    required_keys = ['password', 'confirmPassword']

    if not set(required_keys).issubset(json_payload):
        return jsonify(message='One or more required args were missing from the request'), 400

    if json_payload['password'] != json_payload['confirmPassword']:
        return jsonify(message="Passwords do not match"), 400

    try:
        token_age_limit = key_values_service.get_by_key('password_reset_token_age_limit')
        claim = user_claims_service.validate_and_update_claim(
            type='password_reset',
            token=token,
            email_address=email_address,
            age=token_age_limit['data']['age']
        )
        if not claim:
            return jsonify(message='Invalid token'), 400
    except Exception as error:
        return jsonify(message='Invalid token'), 400

    try:
        publish_tasks.user_claim.delay(
            publish_tasks.compress_user_claim(claim),
            'updated'
        )

        update_user_details(
            password=json_payload['password'],
            user_id=claim.data.get('user_id', None)
        )

        return jsonify(
            message="User with email {}, successfully updated their password".format(email_address),
            email_address=email_address
        ), 200

    except Exception as error:
        return jsonify(message=error.message), 400


@api.route('/generate-api-key/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def generate_api_key_for_user(user_id):
    api_key = api_key_service.generate(user_id)
    if not api_key:
        abort(500, 'Error generating API key')
    return jsonify(key=api_key)


@api.route('/revoke-api-key/<string:key>', methods=['POST'])
@login_required
@role_required('buyer', 'admin')
def revoke_api_key(key):
    api_key = api_key_service.get_key(key)
    is_admin = True if current_user.role == 'admin' else False
    if is_admin or api_key.user.id == current_user.id:
        api_key_service.revoke(key)
        return jsonify(message='API key revoked')
    return jsonify(message='Invalid key'), 400
