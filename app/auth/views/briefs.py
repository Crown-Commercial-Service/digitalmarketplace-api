import os

from flask import abort, jsonify, request, current_app, Response, make_response
from flask_login import current_user, login_required
from app.auth import auth
from app.emails import send_brief_response_received_email
from dmapiclient.audit import AuditTypes
from ...models import db, AuditEvent, Brief, BriefResponse, Supplier, Framework
from sqlalchemy.exc import DataError
from ...utils import (
    get_json_from_request
)
from dmutils.file import s3_upload_file_from_request, s3_download_file
from dmutils.email import hash_email
import mimetypes


def _can_do_brief_response(brief_id):
    try:
        brief = Brief.query.get(brief_id)
    except DataError:
        brief = None

    if brief is None:
        abort(make_response(jsonify(errorMessage="Invalid brief ID '{}'".format(brief_id)), 400))

    if brief.status != 'live':
        abort(make_response(jsonify(errorMessage="Brief must be live"), 400))

    if brief.framework.status != 'live':
        abort(make_response(jsonify(errorMessage="Brief framework must be live"), 400))

    if not hasattr(current_user, 'role') or current_user.role != 'supplier':
        abort(make_response(jsonify(errorMessage="Only supplier role users can respond to briefs"), 403))

    try:
        supplier = Supplier.query.filter(
            Supplier.code == current_user.supplier_code
        ).first()
    except DataError:
        supplier = None

    if not supplier:
        abort(make_response(jsonify(errorMessage="Invalid supplier Code '{}'".format(current_user.supplier_code)), 403))

    def domain(email):
        return email.split('@')[-1]

    current_user_domain = domain(current_user.email_address) \
        if domain(current_user.email_address) not in current_app.config.get('GENERIC_EMAIL_DOMAINS') \
        else None

    if brief.data.get('sellerSelector', '') == 'someSellers':
        seller_domain_list = [domain(x).lower() for x in brief.data['sellerEmailList']]
        if current_user.email_address not in brief.data['sellerEmailList'] \
                and (not current_user_domain or current_user_domain.lower() not in seller_domain_list):
            abort(make_response(jsonify(errorMessage="Supplier not selected for this brief"), 403))
    if brief.data.get('sellerSelector', '') == 'oneSeller':
        if current_user.email_address.lower() != brief.data['sellerEmail'].lower() \
                and (not current_user_domain or
                     current_user_domain.lower() != domain(brief.data['sellerEmail'].lower())):
            abort(make_response(jsonify(errorMessage="Supplier not selected for this brief"), 403))

    if len(supplier.frameworks) == 0 \
            or 'digital-marketplace' != supplier.frameworks[0].framework.slug \
            or len(supplier.assessed_domains) == 0:
        abort(make_response(jsonify(
            errorMessage="Supplier does not have Digital Marketplace framework "
                         "or does not have at least one assessed domain"), 400))

    # Check if brief response already exists from this supplier
    if BriefResponse.query.filter(BriefResponse.supplier == supplier, BriefResponse.brief == brief).first():
        abort(make_response(jsonify(
            errorMessage="Brief response already exists for supplier '{}'".format(supplier.code)), 400))

    return supplier, brief


@auth.route('/brief/<int:brief_id>', methods=["GET"])
def get_brief(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    if brief.status == 'draft':
        brief_user_ids = [user.id for user in brief.users]
        if hasattr(current_user, 'role') and current_user.role == 'buyer' and current_user.id in brief_user_ids:
            return jsonify(brief.serialize(with_users=True))
        else:
            return abort(make_response(jsonify(errorMessage="Unauthorised to view brief or brief does not exist"), 403))
    else:
        return jsonify(brief.serialize(with_users=False))


@auth.route('/brief-response/<int:brief_response_id>', methods=['GET'])
@login_required
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
        abort(make_response(jsonify(errorMessage="Invalid supplier Code '{}'".format(current_user.supplier_code)), 400))
    if supplier.code != brief_response.supplier_code:
        abort(make_response(jsonify(errorMessage="Unauthorised"), 403))

    return jsonify(briefResponses=brief_response.serialize())


@auth.route('/brief/<int:brief_id>/respond/documents/<string:supplier_code>/<slug>', methods=['POST'])
@login_required
def upload_brief_response_file(brief_id, supplier_code, slug):
    supplier, brief = _can_do_brief_response(brief_id)
    return jsonify({"filename": s3_upload_file_from_request(request, slug,
                                                            os.path.join(brief.framework.slug, 'documents',
                                                                         'brief-' + str(brief_id),
                                                                         'supplier-' + str(supplier.code)))
                    })


@auth.route('/brief/<int:brief_id>/respond/documents/<int:supplier_code>/<slug>', methods=['GET'])
@login_required
def download_brief_response_file(brief_id, supplier_code, slug):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    brief_user_ids = [user.id for user in brief.users]
    if hasattr(current_user, 'role') and (current_user.role == 'buyer' and current_user.id in brief_user_ids) \
            or (current_user.role == 'supplier' and current_user.supplier_code == supplier_code):
        file = s3_download_file(slug, os.path.join(brief.framework.slug, 'documents',
                                                   'brief-' + str(brief_id),
                                                   'supplier-' + str(supplier_code)))

        mimetype = mimetypes.guess_type(slug)[0] or 'binary/octet-stream'
        return Response(file, mimetype=mimetype)
    else:
        return abort(make_response(jsonify(errorMessage="Unauthorised to view brief or brief does not exist"), 403))


@auth.route('/brief/<int:brief_id>/respond', methods=["POST"])
@login_required
def post_brief_response(brief_id):
    brief_response_json = get_json_from_request()

    supplier, brief = _can_do_brief_response(brief_id)

    brief_response = BriefResponse(
        data=brief_response_json,
        supplier=supplier,
        brief=brief,
    )

    try:
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
    except Exception as e:
        return jsonify(message=e), 400

    try:
        send_brief_response_received_email(supplier, brief, brief_response)
    except Exception as e:
        rollbar.report_exc_info()
        current_app.logger.error(
            'Send brief response received email failed to send. '
            'error {error} email_hash {email_hash}',
            extra={
                'error': six.text_type(e),
                'email_hash': hash_email(brief_response.data['respondToEmailAddress'])})

    return jsonify(briefResponses=brief_response.serialize()), 201


@auth.route('/framework/<string:framework_slug>', methods=["GET"])
def get_framework(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    return jsonify(framework.serialize())


@auth.route('/supplier/<int:code>', methods=["GET"])
@login_required
def get_supplier(code):
    if hasattr(current_user, 'role') and (current_user.role == 'supplier' and current_user.supplier_code == code):
        supplier = Supplier.query.filter(
            Supplier.code == code
        ).first_or_404()

        return jsonify(supplier.serialize())
    else:
        return abort(make_response(jsonify(errorMessage="Unauthorised to view supplier"), 400))
