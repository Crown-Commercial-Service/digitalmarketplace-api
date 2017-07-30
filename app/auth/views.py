from flask import jsonify, Response
from flask_login import current_user, login_required, logout_user
from app.auth import auth
from app.utils import get_json_from_request, json_has_required_keys
from app.emails.users import send_account_activation_email, send_account_activation_manager_email
from dmutils.email import EmailError
from dmutils.csrf import get_csrf_token
from helpers import get_duplicate_users


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
        json_has_required_keys(json_payload, ['name', 'email_address', ])

        name = json_payload.get('name', None)
        email_address = json_payload.get('email_address', None)
        user_type = json_payload.get('user_type', None)
        employment_status = json_payload.get('employment_status', None)
        line_manager_name = json_payload.get('line_manager_name', None)
        line_manager_email = json_payload.get('line_manager_email', None)

    except ValueError:
        return Response(
            status=400,
            headers=None
        )

    duplicate = get_duplicate_users(email_address=email_address)

    if duplicate and duplicate.values()[0] is not None:
        return Response(
            status=409,
            headers=None,
            response={
                "An account with this email domain already exists"
            }
        )

    if employment_status == 'contractor':
        try:
            send_account_activation_manager_email(
                manager_name=line_manager_name,
                manager_email=line_manager_email,
                applicant_name=name,
                applicant_email=email_address
            )
            return Response(
                status=200,
                headers=None,
                response={"Email invite sent successfully"}
            )

        except EmailError:
            return Response(
                status=400,
                headers=None
            )

    if employment_status == 'employee' or user_type == 'seller':
        try:
            send_account_activation_email(
                name=name,
                email_address=email_address,
                user_type=user_type
            )
            return Response(
                status=200,
                headers=None,
                response={"Email invite sent successfully"}
            )

        except EmailError:
            return Response(
                status=400,
                headers=None
            )

    else:
        return Response(
                status=400,
                headers=None
            )


@auth.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return Response(
        status=200,
        headers=None
    )
