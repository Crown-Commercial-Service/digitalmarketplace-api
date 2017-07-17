from flask import jsonify
from flask_login import current_user, login_required
from app.auth import auth


@auth.route('/ping', methods=["GET"])
def ping():
    return jsonify(isAuthenticated=current_user.is_authenticated)


@auth.route('/protected', methods=["GET"])
@login_required
def protected():
    return jsonify(data='protected')
