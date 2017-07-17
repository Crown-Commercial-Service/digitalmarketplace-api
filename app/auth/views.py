from flask import jsonify, Response
from flask_login import current_user, login_required
from app.auth import auth
from app.utils import get_json_from_request, json_has_required_keys
from app.emails.users import send_account_activation_email
from dmutils.email import EmailError
from helpers import get_duplicate_users


@auth.route('/ping', methods=["GET"])
def ping():
    try:
        user_type = current_user.role
    except AttributeError:
        user_type = 'anonymous'

    return jsonify(
        isAuthenticated=current_user.is_authenticated,
        userType=user_type
    )


@auth.route('/protected', methods=["GET"])
@login_required
def protected():
    return jsonify(data='protected')


@auth.route('/signup', methods=['POST'])
def send_signup_email():
    try:
        json_payload = get_json_from_request()
        json_has_required_keys(json_payload, ['name', 'email_address', ])

        name = json_payload.get('name', None)
        email_address = json_payload.get('email_address', None)
        employment_type = json_payload.get('employment_type', None)
        if employment_type is None:
            user_type = "seller"
        else:
            user_type = "buyer"

    except ValueError as e:
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

    except EmailError as e:
        return Response(
            status=400,
            headers=None
        )
