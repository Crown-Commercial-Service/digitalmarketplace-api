from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError

from app.main import main
from app.models import db, CaseStudy, AuditEvent
from app.utils import (
    get_json_from_request, json_has_required_keys, get_int_or_400,
    pagination_links, get_valid_page_or_1, url_for,
    get_positive_int_or_400, validate_and_return_updater_request
)

from app.service_utils import validate_and_return_supplier

from dmapiclient.audit import AuditTypes


def get_case_study_json():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['caseStudy'])
    return json_payload['caseStudy']


def save_case_study(case_study):
    db.session.add(case_study)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    db.session.commit()


@main.route('/case-studies', methods=['POST'])
def create_case_study():
    case_study_json = get_case_study_json()
    supplier = validate_and_return_supplier(case_study_json)

    case_study = CaseStudy(
        data=case_study_json,
        supplier=supplier
    )
    save_case_study(case_study)

    return jsonify(caseStudy=case_study.serialize()), 201


@main.route('/case-studies/<int:case_study_id>', methods=['PATCH'])
def update_case_study(case_study_id):
    case_study_json = get_case_study_json()

    case_study = CaseStudy.query.get(case_study_id)
    if case_study is None:
        abort(404, "Case study '{}' does not exist".format(case_study_id))

    case_study.update_from_json(case_study_json)
    save_case_study(case_study)

    return jsonify(caseStudy=case_study.serialize()), 200


@main.route('/case-studies/<int:case_study_id>', methods=['GET'])
def get_case_study(case_study_id):
    case_study = CaseStudy.query.filter(
        CaseStudy.id == case_study_id
    ).first_or_404()

    return jsonify(caseStudy=case_study.serialize())


@main.route('/case-studies/<int:case_study_id>', methods=['DELETE'])
def delete_case_study(case_study_id):
    """
    Delete a case study
    :param case_study_id:
    :return:
    """

    updater_json = validate_and_return_updater_request()

    casestudy = CaseStudy.query.filter(
        CaseStudy.id == case_study_id
    ).first_or_404()

    audit = AuditEvent(
        audit_type=AuditTypes.delete_casestudy,
        user=updater_json['updated_by'],
        data={
            "caseStudyId": case_study_id
        },
        db_object=None
    )

    db.session.delete(casestudy)
    db.session.add(audit)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(message="done"), 200


@main.route('/case-studies', methods=['GET'])
def list_case_studies():
    page = get_valid_page_or_1()
    supplier_code = get_int_or_400(request.args, 'supplier_code')

    case_studies = CaseStudy.query
    if supplier_code is not None:
        case_studies = case_studies.filter(CaseStudy.supplier_code == supplier_code)

    if supplier_code:
        return jsonify(
            caseStudies=[case_study.serialize() for case_study in case_studies.all()],
            links={'self': url_for('.list_case_studies', supplier_code=supplier_code)}
        )

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_PAGE_SIZE']
    )

    case_studies = case_studies.paginate(
        page=page,
        per_page=results_per_page
    )

    return jsonify(
        caseStudies=[case_study.serialize() for case_study in case_studies.items],
        links=pagination_links(
            case_studies,
            '.list_case_studies',
            request.args
        )
    )
