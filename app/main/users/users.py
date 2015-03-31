from flask import jsonify

from app.main import main
from app.models import User

@main.route('/users/<string:email_address>', methods=['GET'])
def get_user_by_email(email_address):
    user = User.query.filter(
        User.email_address == email_address
    ).first_or_404()
    return jsonify(users=user.serialize())
