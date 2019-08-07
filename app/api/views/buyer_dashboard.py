from flask import request, jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.business import buyer_dashboard_business
from app.api.helpers import (
    get_email_domain,
    role_required,
    exception_logger
)
from app.api.services import users


@api.route('/buyer/dashboard', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def buyer_dashboard():
    status = request.args.get('status', None)
    result = buyer_dashboard_business.get_briefs(current_user.id, status)
    counts = buyer_dashboard_business.get_brief_counts(current_user.id)

    email_domain = get_email_domain(current_user.email_address)
    organisation = users.get_user_organisation(email_domain)

    return jsonify(
        briefs=result,
        brief_counts=counts,
        organisation=organisation
    ), 200
