from flask import abort, jsonify
from flask_login import current_user
from app.auth import auth
from dmapiclient.audit import AuditTypes
from ...models import db, AuditEvent, Brief, BriefResponse, Supplier, Framework
from sqlalchemy.exc import IntegrityError, DataError
from ...utils import (
    get_json_from_request
)


@auth.route('/brief/<int:brief_id>', methods=["GET"])
def get_brief(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    brief_user_ids = [user.id for user in brief.users]
    if current_user.role == 'buyer' and current_user.id in brief_user_ids:
        return jsonify(brief.serialize(with_users=True))
    else:
        if brief.status == 'draft':
            return abort(403, "Unauthorised to view draft brief")
        else:
            return jsonify(brief.serialize(with_users=False))


@auth.route('/brief-response/<int:brief_response_id>', methods=['GET'])
def get_brief_response(brief_response_id):
    brief_response = BriefResponse.query.filter(
        BriefResponse.id == brief_response_id
    ).first_or_404()

    try:
        supplier = Supplier.query.filter(
            Supplier.code == current_user.supplier_code
        ).first()
    except DataError:
        supplier = None

    if not supplier:
        abort(400, "Invalid supplier Code '{}'".format(current_user.supplier_code))
    if supplier.code != brief_response.supplier_code:
        abort(403, "Unauthorised")

    return jsonify(briefResponses=brief_response.serialize())


@auth.route('/brief/<int:brief_id>/respond', methods=["POST"])
def post_brief_response(brief_id):
    brief_response_json = get_json_from_request()

    try:
        brief = Brief.query.get(brief_id)
    except DataError:
        brief = None

    if brief is None:
        abort(400, "Invalid brief ID '{}'".format(brief_id))

    if brief.status != 'live':
        abort(400, "Brief must be live")

    if brief.framework.status != 'live':
        abort(400, "Brief framework must be live")

    try:
        supplier = Supplier.query.filter(
            Supplier.code == current_user.supplier_code
        ).first()
    except DataError:
        supplier = None

    if not supplier:
        abort(400, "Invalid supplier Code '{}'".format(current_user.supplier_code))

    if len(supplier.frameworks) == 0 \
            or 'digital-marketplace' != supplier.frameworks[0].framework.slug \
            or len(supplier.assessed_domains) == 0:
        abort(400, "Supplier does not have Digital Marketplace framework or does not have at least one assessed domain")

    # FIXME: The UK marketplace checks that the supplier has a relevant service and that its day rate meets the budget.
    # This Australian marketplace should do that too, but Australian suppliers haven't created services yet.

    # Check if brief response already exists from this supplier
    if BriefResponse.query.filter(BriefResponse.supplier == supplier, BriefResponse.brief == brief).first():
        abort(400, "Brief response already exists for supplier '{}'".format(supplier.code))

    brief_response = BriefResponse(
        data=brief_response_json,
        supplier=supplier,
        brief=brief,
    )

    brief_response.validate()

    db.session.add(brief_response)
    db.session.flush()

    audit = AuditEvent(
        audit_type=AuditTypes.create_brief_response,
        user=current_user.email_address,
        data={
            'briefResponseId': brief_response.id,
            'briefResponseJson': brief_response_json,
        },
        db_object=brief_response,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(briefResponses=brief_response.serialize()), 201


@auth.route('/framework/<string:framework_slug>', methods=["GET"])
def get_framework(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    return jsonify(framework.serialize())
