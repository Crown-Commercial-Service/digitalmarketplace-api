from flask import request, jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.business import questions_business
from app.api.helpers import (
    abort,
    forbidden,
    not_found,
    role_required,
    permissions_required,
    exception_logger
)
from app.api.business.errors import (
    NotFoundError,
    ValidationError,
    UnauthorisedError
)
from ...utils import get_json_from_request


@api.route('/brief/<int:brief_id>/questions', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_questions(brief_id):
    result = None
    try:
        result = questions_business.get_questions(current_user, brief_id)
    except NotFoundError as nfe:
        not_found(nfe.message)
    except UnauthorisedError as ue:
        return forbidden(ue.message)

    return jsonify(result), 200


@api.route('/brief/<int:brief_id>/question', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_question(brief_id):
    result = None
    question_id = request.args.get('questionId', None)
    try:
        result = questions_business.get_question(current_user, brief_id, question_id)
    except NotFoundError as nfe:
        not_found(nfe.message)
    except UnauthorisedError as ue:
        return forbidden(ue.message)

    return jsonify(result), 200


@api.route('/brief/<int:brief_id>/answers', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_answers(brief_id):
    result = None
    try:
        result = questions_business.get_answers(brief_id)
    except NotFoundError as nfe:
        return not_found(nfe.message)

    return jsonify(result), 200


@api.route('/brief/<int:brief_id>/publish-answer', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
@permissions_required('answer_seller_questions')
def publish_answer(brief_id):
    data = get_json_from_request()
    try:
        questions_business.publish_answer(current_user, brief_id, data)
    except NotFoundError as nfe:
        return not_found(nfe.message)
    except ValidationError as ve:
        return abort(ve.message)
    except UnauthorisedError as ue:
        return forbidden(ue.message)

    return jsonify(success=True), 200
