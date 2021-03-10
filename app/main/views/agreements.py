from datetime import datetime

from flask import abort
from sqlalchemy.exc import IntegrityError
from dmapiclient.audit import AuditTypes

from .. import main
from ...models import (
    AuditEvent, db, Framework, FrameworkAgreement, SupplierFramework, User
)
from ...utils import (
    get_json_from_request,
    json_has_required_keys,
    json_has_keys,
    single_result_response,
    validate_and_return_updater_request,
)
from ...supplier_utils import validate_agreement_details_data

RESOURCE_NAME = "agreement"

E_SIGNATURE_LIVE_DATE = datetime(2020, 9, 28)


@main.route('/agreements', methods=['POST'])
def create_framework_agreement():
    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(json_payload, ["agreement"])
    update_json = json_payload["agreement"]

    json_has_keys(update_json, required_keys=['supplierId', 'frameworkSlug'])

    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        update_json['supplierId'], update_json['frameworkSlug']
    ).first()

    if not supplier_framework or not supplier_framework.on_framework:
        abort(
            404,
            "supplier_id '{}' is not on framework '{}'".format(
                update_json['supplierId'], update_json['frameworkSlug']
            )
        )

    framework = Framework.query.filter(
        Framework.slug == update_json['frameworkSlug']
    ).first_or_404()

    framework_agreement = FrameworkAgreement(
        supplier_id=update_json['supplierId'],
        framework_id=framework.id
    )
    try:
        db.session.add(framework_agreement)
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit_event = AuditEvent(
        audit_type=AuditTypes.create_agreement,
        user=updater_json['updated_by'],
        data={
            'supplierId': update_json['supplierId'],
            'frameworkSlug': update_json['frameworkSlug']
        },
        db_object=framework_agreement
    )

    db.session.add(audit_event)
    db.session.commit()

    return single_result_response(RESOURCE_NAME, framework_agreement), 201


@main.route('/agreements/<int:agreement_id>', methods=['GET'])
def get_framework_agreement(agreement_id):
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()
    return single_result_response(RESOURCE_NAME, framework_agreement), 200


@main.route('/agreements/<int:agreement_id>', methods=['POST'])
def update_framework_agreement(agreement_id):
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()
    framework_agreement_details = framework_agreement.supplier_framework.framework.framework_agreement_details

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(json_payload, ["agreement"])
    update_json = json_payload["agreement"]

    json_has_keys(
        update_json,
        optional_keys=['signedAgreementDetails', 'signedAgreementPath', 'countersignedAgreementPath']
    )

    if (
        framework_agreement.signed_agreement_returned_at
        and ('signedAgreementDetails' in update_json or 'signedAgreementPath' in update_json)
    ):
        abort(400, "Can not update signedAgreementDetails or signedAgreementPath if agreement has been signed")

    # For G-Cloud 12 onwards (e-signature frameworks), CCS Admins do not have to approve for countersigning
    is_esignature_framework = (
        framework_agreement.supplier_framework.framework.framework_live_at_utc > E_SIGNATURE_LIVE_DATE
    )
    if (
        'countersignedAgreementPath' in update_json and not
        (framework_agreement.countersigned_agreement_returned_at or is_esignature_framework)
    ):
        abort(400, "Can not update countersignedAgreementPath if agreement has not been approved for countersigning")

    if update_json.get('signedAgreementDetails'):
        if not framework_agreement_details or not framework_agreement_details.get('frameworkAgreementVersion'):
            abort(
                400,
                "Can not update signedAgreementDetails for a framework agreement without a frameworkAgreementVersion"
            )

        framework_agreement.update_signed_agreement_details_from_json(update_json['signedAgreementDetails'])
        validate_agreement_details_data(
            framework_agreement.signed_agreement_details,
            enforce_required=False
        )

    if update_json.get('signedAgreementPath'):
        framework_agreement.signed_agreement_path = update_json['signedAgreementPath']
    # Unlike signedAgreementPath, we allow unsetting of countersignedAgreementpath
    if 'countersignedAgreementPath' in update_json:
        framework_agreement.countersigned_agreement_path = update_json['countersignedAgreementPath']

    audit_event = AuditEvent(
        audit_type=AuditTypes.update_agreement,
        user=updater_json['updated_by'],
        data={
            'supplierId': framework_agreement.supplier_id,
            'frameworkSlug': framework_agreement.supplier_framework.framework.slug,
            'update': update_json},
        db_object=framework_agreement
    )

    try:
        db.session.add(framework_agreement)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, framework_agreement), 200


@main.route('/agreements/<int:agreement_id>/sign', methods=['POST'])
def sign_framework_agreement(agreement_id):
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()
    framework_agreement_details = framework_agreement.supplier_framework.framework.framework_agreement_details

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    update_json = None

    if framework_agreement_details and framework_agreement_details.get('frameworkAgreementVersion'):
        json_has_required_keys(json_payload, ["agreement"])
        update_json = json_payload["agreement"]

        json_has_keys(update_json, required_keys=['signedAgreementDetails'])

        framework_agreement.update_signed_agreement_details_from_json(update_json['signedAgreementDetails'])
        framework_agreement.update_signed_agreement_details_from_json(
            {'frameworkAgreementVersion': framework_agreement_details['frameworkAgreementVersion']}
        )
        validate_agreement_details_data(
            framework_agreement.signed_agreement_details,
            enforce_required=True
        )

        if not User.query.filter(User.id == update_json['signedAgreementDetails']['uploaderUserId']).first():
            abort(400, "No user found with id '{}'".format(update_json['signedAgreementDetails']['uploaderUserId']))

    framework_agreement.signed_agreement_returned_at = datetime.utcnow()

    audit_event = AuditEvent(
        audit_type=AuditTypes.sign_agreement,
        user=updater_json['updated_by'],
        data=dict({
            'supplierId': framework_agreement.supplier_id,
            'frameworkSlug': framework_agreement.supplier_framework.framework.slug,
        }, **({'update': update_json} if update_json else {})),
        db_object=framework_agreement
    )

    try:
        db.session.add(framework_agreement)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, framework_agreement), 200


@main.route('/agreements/<int:agreement_id>/on-hold', methods=['POST'])
def put_signed_framework_agreement_on_hold(agreement_id):
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()
    framework_agreement_details = framework_agreement.supplier_framework.framework.framework_agreement_details

    updater_json = validate_and_return_updater_request()

    if framework_agreement.status != 'signed':
        abort(400, "Framework agreement must have status 'signed' to be put on hold")

    if not framework_agreement_details or not framework_agreement_details.get('frameworkAgreementVersion'):
        abort(400, "Framework agreement must have a 'frameworkAgreementVersion' to be put on hold")

    framework_agreement.signed_agreement_put_on_hold_at = datetime.utcnow()

    audit_event = AuditEvent(
        audit_type=AuditTypes.update_agreement,
        user=updater_json['updated_by'],
        data={
            'supplierId': framework_agreement.supplier_id,
            'frameworkSlug': framework_agreement.supplier_framework.framework.slug,
            'status': 'on-hold'
        },
        db_object=framework_agreement
    )

    try:
        db.session.add(framework_agreement)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, framework_agreement), 200


@main.route('/agreements/<int:agreement_id>/approve', methods=['POST'])
def approve_for_countersignature(agreement_id):
    """
    Admin approval is only required for frameworks prior to G-Cloud 12.
    :param agreement_id:
    :return:
    """
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()
    framework_agreement_details = framework_agreement.supplier_framework.framework.framework_agreement_details

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['agreement'])
    update_json = json_payload["agreement"]
    json_has_keys(update_json, required_keys=['userId'], optional_keys=['unapprove'])
    approved_by_user_id = update_json['userId']

    updater_json = validate_and_return_updater_request()

    if 'unapprove' in update_json and update_json['unapprove'] is True:
        if framework_agreement.status != 'approved':
            abort(400, "Framework agreement must have status 'approved' to be unapproved")

        framework_agreement.signed_agreement_put_on_hold_at = None
        framework_agreement.countersigned_agreement_returned_at = None
        framework_agreement.countersigned_agreement_details = None

    else:
        if framework_agreement.status not in ['signed', 'on-hold']:
            abort(400, "Framework agreement must have status 'signed' or 'on hold' to be countersigned")

        framework_agreement.signed_agreement_put_on_hold_at = None
        framework_agreement.countersigned_agreement_returned_at = datetime.utcnow()

        countersigner_details = {}
        if framework_agreement_details:
            if framework_agreement_details.get('countersignerName'):
                countersigner_details.update({
                    'countersignerName': framework_agreement_details['countersignerName']
                })
            if framework_agreement_details.get('countersignerRole'):
                countersigner_details.update({
                    'countersignerRole': framework_agreement_details['countersignerRole']
                })

        countersigner_details.update({'approvedByUserId': approved_by_user_id})
        framework_agreement.countersigned_agreement_details = countersigner_details

    audit_event = AuditEvent(
        audit_type=AuditTypes.countersign_agreement,
        user=updater_json['updated_by'],
        data={
            'supplierId': framework_agreement.supplier_id,
            'frameworkSlug': framework_agreement.supplier_framework.framework.slug,
            'status': 'approved' if framework_agreement.countersigned_agreement_returned_at else 'unapproved'
        },
        db_object=framework_agreement
    )

    try:
        db.session.add(framework_agreement)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, framework_agreement), 200
