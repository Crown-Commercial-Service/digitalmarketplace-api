from app.api import api
from flask import jsonify
from flask_login import current_user, login_required
from app.api.helpers import role_required, exception_logger
from app.api.business.case_study_business import get_approved_case_studies


@api.route('/case-studies/<int:domain_id>/view', methods=['GET'])
@exception_logger
@login_required
@role_required('supplier')
def get_case_studies(domain_id):
    data = get_approved_case_studies(current_user.supplier_code, domain_id)
    return jsonify(data)
