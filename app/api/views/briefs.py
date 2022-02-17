import json
import mimetypes
import os

import botocore
import pendulum
import rollbar
import copy
from flask import Response, current_app, jsonify, request
from flask_login import current_user, login_required
from pendulum.parsing.exceptions import ParserError
from sqlalchemy.exc import DataError

from app.api import api
from app.api.business import (brief_overview_business, brief_training_business,
                              supplier_business)
from app.api.business.agreement_business import use_old_work_order_creator
from app.api.business.brief import BriefUserStatus, brief_business, brief_edit_business
from app.api.business.errors import (BriefError, NotFoundError,
                                     UnauthorisedError)
from app.api.business.validators import (ATMDataValidator, RFXDataValidator,
                                         SpecialistDataValidator,
                                         SupplierValidator,
                                         TrainingDataValidator)
from app.api.csv import generate_brief_responses_csv
from app.api.helpers import (abort, exception_logger, forbidden,
                             get_email_domain, is_current_user_in_brief,
                             not_found, notify_team, permissions_required,
                             role_required, must_be_in_team_check)
from app.api.services import (agency_service, audit_service, audit_types,
                              brief_history_service, brief_question_service,
                              brief_response_download_service,
                              brief_responses_service, briefs, domain_service,
                              evidence_service, frameworks_service,
                              key_values_service, lots_service, suppliers,
                              users, work_order_service)
from app.emails import (render_email_template,
                        send_brief_clarification_to_buyer,
                        send_brief_clarification_to_seller,
                        send_brief_response_received_email,
                        send_seller_invited_to_rfx_email,
                        send_seller_invited_to_training_email,
                        send_specialist_brief_published_email,
                        send_specialist_brief_response_received_email,
                        send_specialist_brief_seller_invited_email)
from app.tasks import publish_tasks
from dmapiclient.audit import AuditTypes
from dmutils.file import s3_download_file, s3_upload_file_from_request

from ...models import (AuditEvent, Brief, BriefQuestion, BriefResponse,
                       BriefResponseDownload, Domain, Framework, Lot, Supplier,
                       User, ValidationError, WorkOrder, db)
from ...utils import get_json_from_request


def _notify_team_brief_published(brief_title, brief_org, user_name, user_email, url):
    notification_message = '{}\n{}\nBy: {} ({})'.format(
        brief_title,
        brief_org,
        user_name,
        user_email
    )
    notify_team('A buyer has published a new opportunity', notification_message, url)


@api.route('/brief/rfx', methods=['POST'])
@login_required
@role_required('buyer')
@must_be_in_team_check
@permissions_required('create_drafts')
def create_rfx_brief():
    """Create RFX brief (role=buyer)
    ---
    tags:
        - brief
    definitions:
        RFXBriefCreated:
            type: object
            properties:
                id:
                    type: number
                lot:
                    type: string
                status:
                    type: string
                author:
                    type: string
    responses:
        200:
            description: Brief created successfully.
            schema:
                $ref: '#/definitions/RFXBriefCreated'
        400:
            description: Bad request.
        403:
            description: Unauthorised to create RFX brief.
        500:
            description: Unexpected error.
    """
    try:
        lot = lots_service.find(slug='rfx').one_or_none()
        framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
        user = users.get(current_user.id)
        brief = briefs.create_brief(user, current_user.get_team(), framework, lot)
    except Exception as e:
        rollbar.report_exc_info()
        return jsonify(message=str(e)), 400

    try:
        audit_service.log_audit_event(
            audit_type=AuditTypes.create_brief,
            user=current_user.email_address,
            data={
                'briefId': brief.id
            },
            db_object=brief)
    except Exception as e:
        rollbar.report_exc_info()

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/training', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
@must_be_in_team_check
@permissions_required('create_drafts')
def create_training_brief():
    brief = brief_training_business.create(current_user)
    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/atm', methods=['POST'])
@login_required
@role_required('buyer')
@must_be_in_team_check
@permissions_required('create_drafts')
def create_atm_brief():
    """Create ATM brief (role=buyer)
    ---
    tags:
        - brief
    definitions:
        ATMBriefCreated:
            type: object
            properties:
                id:
                    type: number
                lot:
                    type: string
                status:
                    type: string
                author:
                    type: string
    responses:
        200:
            description: Brief created successfully.
            schema:
                $ref: '#/definitions/ATMBriefCreated'
        400:
            description: Bad request.
        403:
            description: Unauthorised to create ATM brief.
        500:
            description: Unexpected error.
    """
    try:
        lot = lots_service.find(slug='atm').one_or_none()
        framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
        user = users.get(current_user.id)
        brief = briefs.create_brief(user, current_user.get_team(), framework, lot)
    except Exception as e:
        rollbar.report_exc_info()
        return jsonify(message=str(e)), 400

    try:
        audit_service.log_audit_event(
            audit_type=AuditTypes.create_brief,
            user=current_user.email_address,
            data={
                'briefId': brief.id
            },
            db_object=brief)
    except Exception as e:
        rollbar.report_exc_info()

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/specialist', methods=['POST'])
@login_required
@role_required('buyer')
@must_be_in_team_check
@permissions_required('create_drafts')
def create_specialist_brief():
    """Create Specialist brief (role=buyer)
    ---
    tags:
        - brief
    definitions:
        SpecialistBriefCreated:
            type: object
            properties:
                id:
                    type: number
                lot:
                    type: string
                status:
                    type: string
                author:
                    type: string
    responses:
        200:
            description: Brief created successfully.
            schema:
                $ref: '#/definitions/SpecialistBriefCreated'
        400:
            description: Bad request.
        403:
            description: Unauthorised to create specialist brief.
        500:
            description: Unexpected error.
    """
    try:
        lot = lots_service.find(slug='specialist').one_or_none()
        framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
        user = users.get(current_user.id)
        agency_name = ''
        try:
            agency_name = agency_service.get_agency_name(current_user.agency_id)
        except Exception as e:
            pass
        brief = briefs.create_brief(user, current_user.get_team(), framework, lot, data={
            'organisation': agency_name
        })
    except Exception as e:
        rollbar.report_exc_info()
        return jsonify(message=str(e)), 400

    try:
        audit_service.log_audit_event(
            audit_type=AuditTypes.create_brief,
            user=current_user.email_address,
            data={
                'briefId': brief.id
            },
            db_object=brief)
    except Exception as e:
        rollbar.report_exc_info()

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/<int:brief_id>', methods=["GET"])
def get_brief(brief_id):
    brief = briefs.find(id=brief_id).one_or_none()
    if not brief:
        not_found("No opportunity for id '%s' found" % (brief_id))

    user_role = current_user.role if hasattr(current_user, 'role') else None
    invited_sellers = brief.data['sellers'] if 'sellers' in brief.data else {}

    is_buyer = False
    is_brief_owner = False
    if user_role == 'buyer':
        is_buyer = True
        if briefs.has_permission_to_brief(current_user.id, brief.id):
            is_brief_owner = True

    if brief.status == 'draft' and not is_brief_owner:
        return forbidden("Unauthorised to view opportunity")

    brief_response_count = len(brief_responses_service.get_brief_responses(brief_id, None, submitted_only=True))
    supplier_brief_response_count = 0
    supplier_brief_response_count_submitted = 0
    supplier_brief_response_count_draft = 0
    supplier_brief_response_id = 0
    supplier_brief_response_is_draft = False
    if user_role == 'supplier':
        supplier_brief_responses = brief_responses_service.get_brief_responses(brief_id, current_user.supplier_code)
        supplier_brief_response_count = len(supplier_brief_responses)
        supplier_brief_response_count_submitted = len(
            [x for x in supplier_brief_responses if x['status'] == 'submitted']
        )
        supplier_brief_response_count_draft = len([x for x in supplier_brief_responses if x['status'] == 'draft'])
        if supplier_brief_response_count == 1:
            supplier_brief_response_id = supplier_brief_responses[0]['id']
            supplier_brief_response_is_draft = True if supplier_brief_responses[0]['status'] == 'draft' else False

    invited_seller_count = len(invited_sellers)
    open_to_category = brief.lot.slug == 'atm' and brief.data.get('openTo', '') == 'category'
    is_applicant = user_role == 'applicant'

    # gather facts about the user's status against this brief
    user_status = BriefUserStatus(brief, current_user)
    has_chosen_brief_category = user_status.has_chosen_brief_category()
    has_evidence_in_draft_for_category = user_status.has_evidence_in_draft_for_category()
    has_latest_evidence_rejected_for_category = user_status.has_latest_evidence_rejected_for_category()
    is_assessed_for_category = user_status.is_assessed_for_category()
    is_assessed_in_any_category = user_status.is_assessed_in_any_category()
    is_awaiting_application_assessment = user_status.is_awaiting_application_assessment()
    is_awaiting_domain_assessment = user_status.is_awaiting_domain_assessment()
    has_been_assessed_for_brief = user_status.has_been_assessed_for_brief()
    is_recruiter_only = user_status.is_recruiter_only()
    is_approved_seller = user_status.is_approved_seller()
    is_invited = user_status.is_invited()
    can_respond = user_status.can_respond()
    has_responded = user_status.has_responded()
    evidence_id = user_status.evidence_id_in_draft()
    evidence_id_rejected = user_status.evidence_id_rejected()
    has_supplier_errors = user_status.has_supplier_errors()
    has_signed_current_agreement = user_status.has_signed_current_agreement()
    last_edited_at = brief_history_service.get_last_edited_date(brief.id)
    only_sellers_edited = brief_edit_business.only_sellers_were_edited(brief.id)
    is_consultant = user_status.is_consultant()

    # remove private data for non brief owners
    brief.data['contactEmail'] = ''
    brief.data['users'] = None
    if not is_buyer:
        if 'sellers' in brief.data:
            brief.data['sellers'] = {}
        brief.responses_zip_filesize = None
        brief.data['contactNumber'] = ''
        if not can_respond:
            brief.data['proposalType'] = []
            brief.data['evaluationType'] = []
            brief.data['responseTemplate'] = []
            brief.data['requirementsDocument'] = []
            brief.data['industryBriefing'] = ''
            brief.data['backgroundInformation'] = ''
            brief.data['outcome'] = ''
            brief.data['endUsers'] = ''
            brief.data['workAlreadyDone'] = ''
            brief.data['timeframeConstraints'] = ''
            brief.data['attachments'] = []
    else:
        contacts = briefs.get_brief_contact_details(brief_id)
        if contacts is None:
            not_found('Contact details not found for opportunity {}'.format(brief_id))

        brief.data['contactEmail'] = contacts
        if not is_brief_owner:
            if 'sellers' in brief.data:
                brief.data['sellers'] = {}
            brief.data['industryBriefing'] = ''
            brief.data['contactNumber'] = ''

    domains = []
    for domain in domain_service.get_active_domains():
        domains.append({
            'id': str(domain.id),
            'name': domain.name
        })

    brief_serialized = brief.serialize(with_users=False, with_author=is_brief_owner)
    if not is_buyer:
        if not is_invited:
            brief_serialized['clarificationQuestions'] = []

    return jsonify(brief=brief_serialized,
                   brief_response_count=brief_response_count,
                   invited_seller_count=invited_seller_count,
                   has_chosen_brief_category=has_chosen_brief_category,
                   evidence_id=evidence_id,
                   evidence_id_rejected=evidence_id_rejected,
                   supplier_brief_response_count=supplier_brief_response_count,
                   supplier_brief_response_count_submitted=supplier_brief_response_count_submitted,
                   supplier_brief_response_count_draft=supplier_brief_response_count_draft,
                   supplier_brief_response_id=supplier_brief_response_id,
                   supplier_brief_response_is_draft=supplier_brief_response_is_draft,
                   can_respond=can_respond,
                   has_evidence_in_draft_for_category=has_evidence_in_draft_for_category,
                   has_latest_evidence_rejected_for_category=has_latest_evidence_rejected_for_category,
                   is_assessed_for_category=is_assessed_for_category,
                   is_assessed_in_any_category=is_assessed_in_any_category,
                   is_approved_seller=is_approved_seller,
                   is_awaiting_application_assessment=is_awaiting_application_assessment,
                   is_awaiting_domain_assessment=is_awaiting_domain_assessment,
                   has_been_assessed_for_brief=has_been_assessed_for_brief,
                   open_to_all=brief_business.is_open_to_all(brief),
                   open_to_category=open_to_category,
                   is_brief_owner=is_brief_owner,
                   is_buyer=is_buyer,
                   is_consultant=is_consultant,
                   is_applicant=is_applicant,
                   is_recruiter_only=is_recruiter_only,
                   is_invited=is_invited,
                   has_responded=has_responded,
                   has_supplier_errors=has_supplier_errors,
                   has_signed_current_agreement=has_signed_current_agreement,
                   last_edited_at=last_edited_at,
                   only_sellers_edited=only_sellers_edited,
                   domains=domains)


@api.route('/brief/<int:brief_id>', methods=['PATCH'])
@login_required
@role_required('buyer')
@must_be_in_team_check
def update_brief(brief_id):
    """Update RFX brief (role=buyer)
    ---
    tags:
        - brief
    definitions:
        RFXBrief:
            type: object
            properties:
                title:
                    type: string
                organisation:
                    type: string
                location:
                    type: array
                    items:
                        type: string
                summary:
                    type: string
                industryBriefing:
                    type: string
                sellerCategory:
                    type: string
                sellers:
                    type: object
                attachments:
                    type: array
                    items:
                        type: string
                requirementsDocument:
                    type: array
                    items:
                        type: string
                responseTemplate:
                    type: array
                    items:
                        type: string
                evaluationType:
                    type: array
                    items:
                        type: string
                proposalType:
                    type: array
                    items:
                        type: string
                evaluationCriteria:
                    type: array
                    items:
                        type: object
                includeWeightings:
                    type: boolean
                closedAt:
                    type: string
                contactNumber:
                    type: string
                startDate:
                    type: string
                contractLength:
                    type: string
                contractExtensions:
                    type: string
                budgetRange:
                    type: string
                workingArrangements:
                    type: string
                securityClearance:
                    type: string
    parameters:
      - name: brief_id
        in: path
        type: number
        required: true
      - name: body
        in: body
        required: true
        schema:
            $ref: '#/definitions/RFXBrief'
    responses:
        200:
            description: Brief updated successfully.
            schema:
                $ref: '#/definitions/RFXBrief'
        400:
            description: Bad request.
        403:
            description: Unauthorised to update RFX brief.
        404:
            description: Brief not found.
        500:
            description: Unexpected error.
    """
    brief = briefs.get(brief_id)

    if not brief:
        not_found("Invalid opportunity id '{}'".format(brief_id))

    if brief.status != 'draft':
        abort('Cannot edit a {} opportunity'.format(brief.status))

    if brief.lot.slug not in ['rfx', 'atm', 'specialist', 'training2']:
        abort('Opportunity lot not supported for editing')

    if current_user.role == 'buyer':
        if not briefs.has_permission_to_brief(current_user.id, brief.id):
            return forbidden('Unauthorised to update opportunity')

    data = get_json_from_request()

    publish = False
    if 'publish' in data and data['publish']:
        del data['publish']
        publish = True
        if not current_user.has_permission('publish_opportunities'):
            return forbidden('Unauthorised to publish opportunity')
    else:
        if not (
            current_user.has_permission('create_drafts') or
            current_user.has_permission('publish_opportunities')
        ):
            return forbidden('Unauthorised to edit drafts')

    data_to_validate = copy.deepcopy(data)
    if brief.lot.slug == 'rfx':
        # validate the RFX JSON request data
        errors = RFXDataValidator(data_to_validate).validate(publish=publish)
        if len(errors) > 0:
            abort(', '.join(errors))

    if brief.lot.slug == 'training2':
        # validate the training JSON request data
        errors = TrainingDataValidator(data_to_validate).validate(publish=publish)
        if len(errors) > 0:
            abort(', '.join(errors))

    if brief.lot.slug == 'atm':
        # validate the ATM JSON request data
        errors = ATMDataValidator(data_to_validate).validate(publish=publish)
        if len(errors) > 0:
            abort(', '.join(errors))

    if brief.lot.slug == 'specialist':
        # validate the specialist JSON request data
        errors = SpecialistDataValidator(data_to_validate).validate(publish=publish)
        if len(errors) > 0:
            abort(', '.join(errors))

    if brief.lot.slug in ['rfx', 'training2'] and 'evaluationType' in data:
        if 'Written proposal' not in data['evaluationType']:
            data['proposalType'] = []
        if 'Response template' not in data['evaluationType']:
            data['responseTemplate'] = []

    if brief.lot.slug in ['rfx', 'training2'] and 'sellers' in data and len(data['sellers']) > 0:
        data['sellerSelector'] = 'someSellers' if len(data['sellers']) > 1 else 'oneSeller'

    data['areaOfExpertise'] = ''
    if brief.lot.slug in ['atm', 'specialist'] and 'openTo' in data:
        if data['openTo'] == 'all':
            data['sellerSelector'] = 'allSellers'
            if brief.lot.slug in ['atm']:
                data['sellerCategory'] = ''
        elif data['openTo'] in ['category', 'selected']:
            data['sellerSelector'] = 'someSellers'

        if data['sellerCategory']:
            brief_domain = domain_service.get_by_name_or_id(int(data['sellerCategory']))
            if brief_domain:
                data['areaOfExpertise'] = brief_domain.name
        else:
            data['areaOfExpertise'] = ''

    for requirement in data.get('evaluationCriteria', []):
        if 'criteria' in requirement:
            requirement['criteria'] = requirement['criteria'].replace('\\', '/')

    for requirement in data.get('essentialRequirements', []):
        if 'criteria' in requirement:
            requirement['criteria'] = requirement['criteria'].replace('\\', '/')

    for requirement in data.get('niceToHaveRequirements', []):
        if 'criteria' in requirement:
            requirement['criteria'] = requirement['criteria'].replace('\\', '/')

    previous_status = brief.status
    brief.data = data
    if publish:
        brief.publish(closed_at=data['closedAt'])
    briefs.save_brief(brief)

    if publish:
        if 'sellers' in brief.data and data['sellerSelector'] != 'allSellers':
            for seller_code, seller in brief.data['sellers'].items():
                supplier = suppliers.get_supplier_by_code(seller_code)
                if brief.lot.slug == 'rfx':
                    send_seller_invited_to_rfx_email(brief, supplier)

                send_seller_invited_to_training_email(brief, supplier)
                send_specialist_brief_seller_invited_email(brief, supplier)

        send_specialist_brief_published_email(brief)

        try:
            brief_url_external = '{}/2/digital-marketplace/opportunities/{}'.format(
                current_app.config['FRONTEND_ADDRESS'],
                brief_id
            )
            _notify_team_brief_published(
                brief.data['title'],
                brief.data['organisation'],
                current_user.name,
                current_user.email_address,
                brief_url_external
            )
        except Exception as e:
            pass

        brief_url_external = '{}/2/digital-marketplace/opportunities/{}'.format(
            current_app.config['FRONTEND_ADDRESS'],
            brief_id
        )

        publish_tasks.brief.delay(
            publish_tasks.compress_brief(brief),
            'published',
            previous_status=previous_status,
            name=current_user.name,
            email_address=current_user.email_address,
            url=brief_url_external
        )

    try:
        audit_service.log_audit_event(
            audit_type=AuditTypes.update_brief,
            user=current_user.email_address,
            data={
                'briefId': brief.id,
                'briefData': brief.data
            },
            db_object=brief)
    except Exception as e:
        rollbar.report_exc_info()

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/<int:brief_id>/close', methods=['POST'])
@exception_logger
@login_required
@permissions_required('publish_opportunities')
@role_required('buyer')
@must_be_in_team_check
def close_opportunity_early(brief_id):
    try:
        brief = brief_overview_business.close_opportunity_early(current_user.id, brief_id)
    except NotFoundError as e:
        not_found(str(e))
    except UnauthorisedError as e:
        forbidden(str(e))
    except BriefError as e:
        abort(str(e))

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/<int:brief_id>/edit', methods=['GET'])
@exception_logger
@login_required
@permissions_required('publish_opportunities')
@role_required('buyer')
@must_be_in_team_check
def get_opportunity_to_edit(brief_id):
    try:
        data = brief_edit_business.get_opportunity_to_edit(current_user.id, brief_id)
    except NotFoundError as e:
        not_found(str(e))
    except UnauthorisedError as e:
        forbidden(str(e))
    except BriefError as e:
        abort(str(e))

    return jsonify(data)


@api.route('/brief/<int:brief_id>/edit', methods=['PATCH'])
@exception_logger
@login_required
@permissions_required('publish_opportunities')
@role_required('buyer')
@must_be_in_team_check
def edit_opportunity(brief_id):
    edits = get_json_from_request()

    try:
        brief = brief_edit_business.edit_opportunity(current_user.id, brief_id, edits)
    except NotFoundError as e:
        not_found(str(e))
    except UnauthorisedError as e:
        forbidden(str(e))
    except ValidationError as e:
        abort(str(e))
    except BriefError as e:
        abort(str(e))

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/<int:brief_id>/history', methods=['GET'])
@exception_logger
def get_opportunity_history(brief_id):
    brief = briefs.get(brief_id)
    if not brief:
        not_found("Invalid opportunity id '{}'".format(brief_id))

    user_role = current_user.role if hasattr(current_user, 'role') else None
    show_documents = False
    user_status = BriefUserStatus(brief, current_user)
    can_respond = user_status.can_respond()

    if user_role == 'supplier':
        show_documents = can_respond
    elif user_role in ['buyer', 'admin']:
        show_documents = True

    try:
        edits = brief_edit_business.get_opportunity_history(brief_id, show_documents, include_sellers=False)
    except NotFoundError as e:
        not_found(str(e))

    edits['can_respond'] = can_respond
    if (user_role == 'supplier' and not can_respond) or user_role not in ['admin', 'buyer', 'supplier']:
        edits['edits'] = []

    return jsonify(edits)


@api.route('/brief/<int:brief_id>/withdraw', methods=['POST'])
@exception_logger
@login_required
@permissions_required('publish_opportunities')
@role_required('buyer')
@must_be_in_team_check
def withdraw_opportunity(brief_id):
    data = get_json_from_request()

    try:
        brief = brief_overview_business.withdraw_opportunity(
            current_user.id,
            brief_id,
            data.get('reasonToWithdraw', '')
        )
    except NotFoundError as e:
        not_found(str(e))
    except UnauthorisedError as e:
        forbidden(str(e))
    except (BriefError, ValidationError) as e:
        abort(str(e))

    return jsonify(brief.serialize(with_users=False))


@api.route('/brief/<int:brief_id>', methods=['DELETE'])
@login_required
@role_required('buyer')
@must_be_in_team_check
def delete_brief(brief_id):
    """Delete brief (role=buyer)
    ---
    tags:
        - brief
    definitions:
        DeleteBrief:
            type: object
            properties:
                message:
                    type: string
    parameters:
      - name: brief_id
        in: path
        type: number
        required: true
    responses:
        200:
            description: Brief deleted successfully.
            schema:
                $ref: '#/definitions/DeleteBrief'
        400:
            description: Bad request. Brief status must be 'draft'.
        403:
            description: Unauthorised to delete brief.
        404:
            description: brief_id not found.
        500:
            description: Unexpected error.
    """
    brief = briefs.get(brief_id)

    if not brief:
        not_found("Invalid opportunity id '{}'".format(brief_id))

    if not (
        current_user.has_permission('create_drafts') or
        current_user.has_permission('publish_opportunities')
    ):
        return forbidden('Unauthorised to edit drafts')

    if current_user.role == 'buyer':
        if not briefs.has_permission_to_brief(current_user.id, brief.id):
            return forbidden('Unauthorised to delete opportunity')

    if brief.status != 'draft':
        abort('Cannot delete a {} opportunity'.format(brief.status))

    audit = AuditEvent(
        audit_type=AuditTypes.delete_brief,
        user=current_user.email_address,
        data={
            'briefId': brief_id
        },
        db_object=None
    )

    try:
        deleted_brief = publish_tasks.compress_brief(brief)
        audit_service.save(audit)
        briefs.delete(brief)
        publish_tasks.brief.delay(
            deleted_brief,
            'deleted',
            user=current_user.email_address
        )
    except Exception as e:
        extra_data = {'audit_type': AuditTypes.delete_brief, 'briefId': brief.id, 'exception': str(e)}
        rollbar.report_exc_info(extra_data=extra_data)

    return jsonify(message='Opportunity {} deleted'.format(brief_id)), 200


@api.route('/brief/<int:brief_id>/overview', methods=["GET"])
@login_required
@role_required('buyer')
def get_brief_overview(brief_id):
    """Overview (role=buyer)
    ---
    tags:
        - brief
    definitions:
        BriefOverview:
            type: object
            properties:
                sections:
                    type: array
                    items:
                        $ref: '#/definitions/BriefOverviewSections'
                title:
                    type: string
        BriefOverviewSections:
            type: array
            items:
                $ref: '#/definitions/BriefOverviewSection'
        BriefOverviewSection:
            type: object
            properties:
                links:
                    type: array
                    items:
                        $ref: '#/definitions/BriefOverviewSectionLinks'
                title:
                    type: string
        BriefOverviewSectionLinks:
            type: array
            items:
                $ref: '#/definitions/BriefOverviewSectionLink'
        BriefOverviewSectionLink:
            type: object
            properties:
                complete:
                    type: boolean
                path:
                    type: string
                    nullable: true
                text:
                    type: string
    responses:
        200:
            description: Data for the Overview page
            schema:
                $ref: '#/definitions/BriefOverview'
        400:
            description: Lot not supported.
        403:
            description: Unauthorised to view brief.
        404:
            description: brief_id not found
    """
    brief = briefs.get(brief_id)

    if not brief:
        not_found("Invalid opportunity id '{}'".format(brief_id))

    if current_user.role == 'buyer':
        if not briefs.has_permission_to_brief(current_user.id, brief.id):
            return forbidden('Unauthorised to view opportunity')

    if not (brief.lot.slug == 'digital-professionals' or
            brief.lot.slug == 'training'):
        abort('Lot {} is not supported'.format(brief.lot.slug))

    sections = brief_overview_business.get_sections(brief)

    return jsonify(
        sections=sections,
        lot_slug=brief.lot.slug,
        status=brief.status,
        title=brief.data['title']
    ), 200


@api.route('/brief/<int:brief_id>/responses', methods=['GET'])
@login_required
def get_brief_responses(brief_id):
    brief = briefs.get(brief_id)
    if not brief:
        not_found("Invalid opportunity id '{}'".format(brief_id))

    if current_user.role == 'buyer':
        if not briefs.has_permission_to_brief(current_user.id, brief.id):
            return forbidden("Unauthorised to view opportunity or opportunity does not exist")

    supplier_code = getattr(current_user, 'supplier_code', None)
    supplier_contact = None
    if current_user.role == 'supplier':
        validation_result = supplier_business.get_supplier_messages(supplier_code, True)
        if len(validation_result.errors) > 0:
            abort(validation_result.errors)

        supplier = suppliers.find(code=supplier_code).one_or_none()
        if supplier:
            supplier_contact = {
                'email': supplier.data.get('contact_email'),
                'phone': supplier.data.get('contact_phone')
            }
        # strip data from seller view
        if 'sellers' in brief.data:
            brief.data['sellers'] = {}
        if brief.responses_zip_filesize:
            brief.responses_zip_filesize = None
        if 'industryBriefing' in brief.data:
            brief.data['industryBriefing'] = ''
        if 'attachments' in brief.data:
            brief.data['attachments'] = []
        if 'backgroundInformation' in brief.data:
            brief.data['backgroundInformation'] = ''
        if 'outcome' in brief.data:
            brief.data['outcome'] = ''
        if 'endUsers' in brief.data:
            brief.data['endUsers'] = ''
        if 'workAlreadyDone' in brief.data:
            brief.data['workAlreadyDone'] = ''
        if 'timeframeConstraints' in brief.data:
            brief.data['timeframeConstraints'] = ''
        if 'contactNumber' in brief.data:
            brief.data['contactNumber'] = ''

    questions_asked = 0
    brief_response_downloaded = []
    brief_responses = []
    if current_user.role == 'buyer':
        if brief.status == 'closed':
            brief_response_downloaded = brief_response_download_service.get_responses_downloaded(brief.id)
            brief_responses = brief_responses_service.get_brief_responses(brief_id, supplier_code, submitted_only=True)
        if brief.status in ['closed', 'live']:
            questions_asked = len(brief_question_service.find(brief_id=brief.id).all())
        # enrich the invited sellers data for brief owners
        if 'sellers' in brief.data:
            for seller_code in brief.data['sellers']:
                supplier = suppliers.get_supplier_by_code(seller_code)
                if supplier:
                    brief.data['sellers'][seller_code]['email'] = supplier.data.get('contact_email', None)
                    brief.data['sellers'][seller_code]['number'] = supplier.data.get('contact_phone', None)
                    brief_responses_by_seller = brief_responses_service.get_brief_responses(
                        brief_id, seller_code, submitted_only=True
                    )
                    brief.data['sellers'][seller_code]['has_responded'] = (
                        True if len(brief_responses_by_seller) > 0 else False
                    )
                    brief.data['sellers'][seller_code]['response_count'] = len(brief_responses_by_seller)
    else:
        brief_responses = brief_responses_service.get_brief_responses(brief_id, supplier_code, order_by_status=True)

    old_work_order_creator = use_old_work_order_creator(brief.published_at)

    return jsonify(brief=brief.serialize(with_users=False, with_author=False),
                   briefResponses=brief_responses,
                   canCloseOpportunity=brief_overview_business.can_close_opportunity_early(brief),
                   isOpenToAll=brief_business.is_open_to_all(brief),
                   oldWorkOrderCreator=old_work_order_creator,
                   questionsAsked=questions_asked,
                   briefResponseDownloaded=brief_response_downloaded,
                   supplierContact=supplier_contact)


@api.route('/brief/<int:brief_id>/respond/documents/<string:supplier_code>/<slug>', methods=['POST'])
@login_required
@role_required('supplier')
def upload_brief_response_file(brief_id, supplier_code, slug):
    brief = briefs.get(brief_id)
    if not brief or brief.status != 'live':
        not_found("Invalid opportunity id '{}'".format(brief_id))
    if str(current_user.supplier_code) != str(supplier_code):
        forbidden('User supplier does not match the supplier code in the request')
    user_status = BriefUserStatus(brief, current_user)
    if not user_status.can_respond():
        forbidden('User supplier can not submit documents to this opportunity')
    return jsonify(
        {
            "filename": s3_upload_file_from_request(
                request,
                slug,
                os.path.join(
                    brief.framework.slug, 'documents', 'brief-' + str(brief_id), 'supplier-' + str(supplier_code)
                )
            )
        }
    )


@api.route('/brief/<int:brief_id>/attachments/<slug>', methods=['POST'])
@login_required
@role_required('buyer')
@must_be_in_team_check
def upload_brief_rfx_attachment_file(brief_id, slug):
    """Add brief attachments (role=buyer)
    ---
    tags:
        - brief
    parameters:
      - name: brief_id
        in: path
        type: number
        required: true
      - name: slug
        in: path
        type: string
        required: true
      - name: file
        in: body
        required: true
    responses:
        200:
            description: Attachment uploaded successfully.
        403:
            description: Unauthorised to update brief.
        404:
            description: Brief not found.
        500:
            description: Unexpected error.
    """
    brief = briefs.get(brief_id)

    if not brief:
        not_found("Invalid opportunity id '{}'".format(brief_id))

    if not briefs.has_permission_to_brief(current_user.id, brief.id):
        return forbidden('Unauthorised to update opportunity')

    try:
        filename = s3_upload_file_from_request(
            request, slug, os.path.join(brief.framework.slug, 'attachments', 'brief-' + str(brief_id))
        )
    except Exception as e:
        abort(str(e))

    return jsonify({"filename": filename})


@api.route('/brief/<int:brief_id>/respond/documents')
@login_required
@role_required('buyer')
@must_be_in_team_check
@permissions_required('download_responses')
def download_brief_responses(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    if not briefs.has_permission_to_brief(current_user.id, brief.id):
        return forbidden("Unauthorised to view opportunity or opportunity does not exist")
    if brief.status != 'closed':
        return forbidden("You can only download documents for closed opportunities")

    response = ('', 404)
    brief_response_download_service.save(BriefResponseDownload(
        brief_id=brief.id,
        user_id=current_user.id
    ))
    if brief.lot.slug in ['digital-professionals', 'training', 'rfx', 'training2', 'atm', 'specialist']:
        response = Response(
            s3_download_file(
                current_app.config.get('S3_BUCKET_NAME'),
                'brief-{}-resumes.zip'.format(brief_id),
                os.path.join(brief.framework.slug, 'archives', 'brief-{}'.format(brief_id))
            ),
            mimetype='application/zip'
        )
        response.headers['Content-Disposition'] = 'attachment; filename="opportunity-{}-responses.zip"'.format(brief_id)
    elif brief.lot.slug == 'digital-outcome':
        responses = BriefResponse.query.filter(
            BriefResponse.brief_id == brief_id,
            BriefResponse.withdrawn_at.is_(None)
        ).all()
        csvdata = generate_brief_responses_csv(brief, responses)
        response = Response(csvdata, mimetype='text/csv')
        response.headers['Content-Disposition'] = (
            'attachment; filename="responses-to-requirements-{}.csv"'.format(brief_id))

    return response


@api.route('/brief/<int:brief_id>/attachments/<slug>', methods=['GET'])
@login_required
def download_brief_attachment(brief_id, slug):
    """Get brief attachments.
    ---
    tags:
        - brief
    parameters:
      - name: brief_id
        in: path
        type: number
        required: true
      - name: slug
        in: path
        type: string
        required: true
    responses:
        200:
            description: Attachment retrieved successfully.
        404:
            description: Attachment not found.
        500:
            description: Unexpected error.
    """
    brief = briefs.get(brief_id)

    if not brief:
        return not_found('File not found')

    user_role = current_user.role if hasattr(current_user, 'role') else None
    user_status = BriefUserStatus(brief, current_user)

    all_documents = (
        brief.data.get('attachments', []) +
        brief.data.get('requirementsDocument', []) +
        brief.data.get('responseTemplate', [])
    )

    if (
        user_role == 'admin' or
        user_role == 'buyer' or (
            user_role == 'supplier' and
            user_status.can_respond() and
            slug in all_documents
        )
    ):
        mimetype = mimetypes.guess_type(slug)[0] or 'binary/octet-stream'
        return Response(
            s3_download_file(
                current_app.config.get('S3_BUCKET_NAME'),
                slug,
                os.path.join(brief.framework.slug, 'attachments', 'brief-' + str(brief_id))
            ),
            mimetype=mimetype
        )
    else:
        return not_found('File not found')


@api.route('/brief/<int:brief_id>/respond/documents/<int:supplier_code>/<slug>', methods=['GET'])
@login_required
def download_brief_response_file(brief_id, supplier_code, slug):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    if (
        hasattr(current_user, 'role') and (
            current_user.role == 'buyer' and
            briefs.has_permission_to_brief(current_user.id, brief.id)
        ) or (
            current_user.role == 'supplier' and
            current_user.supplier_code == supplier_code
        )
    ):
        mimetype = mimetypes.guess_type(slug)[0] or 'binary/octet-stream'
        return Response(
            s3_download_file(
                current_app.config.get('S3_BUCKET_NAME'),
                slug,
                os.path.join(
                    brief.framework.slug, 'documents', 'brief-' + str(brief_id), 'supplier-' + str(supplier_code)
                )
            ),
            mimetype=mimetype
        )
    else:
        return forbidden("Unauthorised to view opportunity or opportunity does not exist")


@api.route('/brief/<int:brief_id>/respond', methods=['POST'])
@exception_logger
@login_required
@role_required('supplier')
def create_brief_response(brief_id):
    brief = briefs.get(brief_id)
    if not brief or brief.status != 'live':
        not_found("Invalid opportunity id '{}'".format(brief_id))
    supplier = suppliers.get_supplier_by_code(current_user.supplier_code, include_deleted=False)
    if not supplier:
        abort('User supplier is invalid')

    can_respond, error_message = brief_business.can_submit_response_to_brief(brief, current_user)
    if not can_respond:
        return jsonify(message=error_message), 400

    try:
        brief_response = brief_responses_service.create(
            supplier=supplier,
            brief=brief,
            data={}
        )
    except Exception as e:
        rollbar.report_exc_info()
        return jsonify(message=str(e)), 400

    try:
        audit_service.log_audit_event(
            audit_type=AuditTypes.create_brief_response,
            user=current_user.email_address,
            data={
                'briefResponseId': brief_response.id
            },
            db_object=brief_response
        )
        publish_tasks.brief_response.delay(
            publish_tasks.compress_brief_response(brief_response),
            'created',
            user=current_user.email_address
        )
    except Exception as e:
        rollbar.report_exc_info()

    return jsonify(brief_response.serialize()), 201


@api.route('/brief/<int:brief_id>/respond/<int:brief_response_id>', methods=['PATCH'])
@exception_logger
@login_required
@role_required('supplier')
def update_brief_response(brief_id, brief_response_id):
    brief = briefs.get(brief_id)
    if not brief or brief.status != 'live':
        not_found("Invalid opportunity id '{}'".format(brief_id))
    supplier = suppliers.get_supplier_by_code(current_user.supplier_code, include_deleted=False)
    if not supplier:
        abort('User supplier is invalid')

    can_respond, error_message = brief_business.can_submit_response_to_brief(
        brief, current_user, check_response_limit=False
    )
    if not can_respond:
        return jsonify(message=error_message), 400

    brief_response = brief_responses_service.find(
        id=brief_response_id,
        brief_id=brief.id,
        supplier_code=supplier.code,
        withdrawn_at=None
    ).one_or_none()
    if not brief_response or brief_response.status not in ['submitted', 'draft']:
        not_found('This response does not exist or has been withdrawn')
    if brief.status != 'live':
        abort('Opportunity responses can only be edited when the opportunity is still live')

    submit = False
    brief_response_json = get_json_from_request()
    if 'submit' in brief_response_json:
        if brief_response_json['submit']:
            submit = True
        del brief_response_json['submit']

    # if the current brief response is already submitted and it doesn't have the required upload file fields, then
    # flag the required file check as unnecessary as this would be an old response before the introduction of the
    # individual file fields in the brief response
    do_required_file_check = True
    if brief_response.status == 'submitted' and (
        len(brief_response.data.get('resume', [])) == 0 and
        len(brief_response.data.get('responseTemplate', [])) == 0 and
        len(brief_response.data.get('writtenProposal', [])) == 0
    ):
        do_required_file_check = False

    previous_status = brief_response.status
    brief_response.data = brief_response_json
    if submit:
        try:
            brief_response.validate(do_required_file_check=do_required_file_check)
        except ValidationError as e:
            try:
                errors = e.message
            except AttributeError:
                (errors,) = e.args

            brief_response_json['brief_id'] = brief_id
            rollbar.report_exc_info(extra_data=brief_response_json)
            message = ""
            if 'essentialRequirements' in errors and errors['essentialRequirements'] == 'answer_required':
                message = "Essential requirements must be completed"
                del errors['essentialRequirements']
            if 'attachedDocumentURL' in errors:
                if not do_required_file_check and errors['attachedDocumentURL'] == 'answer_required':
                    message = "Documents must be uploaded"
                if errors['attachedDocumentURL'] == 'file_incorrect_format':
                    message = "Uploaded documents are in the wrong format"
                del errors['attachedDocumentURL']
            if 'resume' in errors:
                if do_required_file_check and errors['resume'] == 'answer_required':
                    message = "Resume must be uploaded"
                if errors['resume'] == 'file_incorrect_format':
                    message = "Uploaded documents are in the wrong format"
                del errors['resume']
            if 'responseTemplate' in errors:
                if do_required_file_check and errors['responseTemplate'] == 'answer_required':
                    message = "Response template must be uploaded"
                if errors['responseTemplate'] == 'file_incorrect_format':
                    message = "Uploaded documents are in the wrong format"
                del errors['responseTemplate']
            if 'writtenProposal' in errors:
                if do_required_file_check and errors['writtenProposal'] == 'answer_required':
                    message = "Written proposal must be uploaded"
                if errors['writtenProposal'] == 'file_incorrect_format':
                    message = "Uploaded documents are in the wrong format"
                del errors['writtenProposal']
            if 'criteria' in errors and errors['criteria'] == 'answer_required':
                message = "Criteria must be completed"

            for field in [{
                'name': 'specialistGivenNames',
                'label': 'Given names'
            }, {
                'name': 'specialistSurname',
                'label': 'Surname'
            }, {
                'name': 'dayRateExcludingGST',
                'label': 'Daily rate (excluding GST)'
            }, {
                'name': 'dayRate',
                'label': 'Daily rate'
            }, {
                'name': 'hourRateExcludingGST',
                'label': 'Hourly rate (excluding GST)'
            }, {
                'name': 'hourRate',
                'label': 'Hourly rate'
            }, {
                'name': 'visaStatus',
                'label': 'Eligibility to work'
            }, {
                'name': 'securityClearance',
                'label': 'Security clearance'
            }, {
                'name': 'previouslyWorked',
                'label': 'Previously worked'
            }]:
                if field['name'] in errors and errors[field['name']] == 'answer_required':
                    message += '{} is required\n'.format(field['label'])
                    del errors[field['name']]

            if len(errors) > 0:
                message += json.dumps(errors)
            return jsonify(message=message), 400
        except Exception as e:
            brief_response_json['brief_id'] = brief_id
            rollbar.report_exc_info(extra_data=brief_response_json)
            return jsonify(message=str(e)), 400

        brief_response.submit()
        try:
            if brief.lot.slug == 'specialist':
                if previous_status == 'draft':
                    send_specialist_brief_response_received_email(supplier, brief, brief_response)
                if previous_status == 'submitted':
                    send_specialist_brief_response_received_email(
                        supplier, brief, brief_response, supplier_user=current_user.name, is_update=True
                    )
            else:
                if previous_status == 'draft':
                    send_brief_response_received_email(supplier, brief, brief_response)
                if previous_status == 'submitted':
                    send_brief_response_received_email(
                        supplier, brief, brief_response, supplier_user=current_user.name, is_update=True
                    )
        except Exception as e:
            brief_response_json['brief_id'] = brief_id
            rollbar.report_exc_info(extra_data=brief_response_json)
    brief_responses_service.save(brief_response)
    try:
        audit_service.log_audit_event(
            audit_type=audit_types.update_brief_response,
            user=current_user.email_address,
            data={
                'briefResponseId': brief_response.id,
                'briefResponseJson': brief_response_json,
                'submitted': submit
            },
            db_object=brief_response
        )

        publish_tasks.brief_response.delay(
            publish_tasks.compress_brief_response(brief_response),
            'submitted' if submit else 'saved',
            user=current_user.email_address
        )
    except Exception as e:
        rollbar.report_exc_info()

    response_data = brief_response.serialize()
    response_data['previous_status'] = previous_status
    return jsonify(response_data), 200


@api.route('/framework/<string:framework_slug>', methods=["GET"])
def get_framework(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    return jsonify(framework.serialize())


@api.route('/brief/<int:brief_id>/assessors', methods=["GET"])
@login_required
@role_required('buyer')
@is_current_user_in_brief
def get_assessors(brief_id):
    """All brief assessors (role=buyer)
    ---
    tags:
      - brief
    security:
      - basicAuth: []
    parameters:
      - name: brief_id
        in: path
        type: number
        required: true
    definitions:
      BriefAssessors:
        type: array
        items:
          $ref: '#/definitions/BriefAssessor'
      BriefAssessor:
        type: object
        properties:
          id:
            type: integer
          brief_id:
            type: integer
          user_id:
            type: integer
          email_address:
            type: string
          user_email_address:
            type: string
    responses:
      200:
        description: A list of brief assessors
        schema:
          $ref: '#/definitions/BriefAssessors'
    """
    assessors = briefs.get_assessors(brief_id)
    return jsonify(assessors)


@api.route('/brief/<int:brief_id>/notification/<string:template>', methods=["GET"])
def get_notification_template(brief_id, template):
    brief = briefs.get(brief_id)
    if brief:
        frontend_url = current_app.config['FRONTEND_ADDRESS']
        return render_email_template(
            '{}.md'.format(template),
            frontend_url=frontend_url,
            brief_name=brief.data['title'],
            brief_id=brief.id,
            brief_url='{}/digital-marketplace/opportunities/{}'.format(frontend_url, brief_id)
        )

    return not_found('Opportunity not found')


@api.route('/brief/<int:brief_id>/award-seller', methods=['POST'])
@login_required
@role_required('buyer')
@must_be_in_team_check
@permissions_required('create_work_orders')
def award_brief_to_seller(brief_id):
    """Award a brief to a seller (role=buyer)
    ---
    tags:
        - brief
    definitions:
        BriefAwarded:
            type: object
            properties:
                awardedSupplier:
                    type: string
    responses:
        200:
            description: Brief awarded successfully.
            schema:
                $ref: '#/definitions/BriefAwarded'
        400:
            description: Bad request.
        403:
            description: Unauthorised to award brief to seller.
        500:
            description: Unexpected error.
    """
    brief = briefs.get(brief_id)
    if not brief:
        return not_found('Opportunity {} not found'.format(brief_id))

    if not briefs.has_permission_to_brief(current_user.id, brief.id):
        return forbidden('Unauthorised to award opportunity to seller')

    data = get_json_from_request()
    supplier_code = data.get('awardedSupplierCode')
    if not supplier_code:
        return abort('Supplier is required.')

    work_order = work_order_service.find(brief_id=brief_id).one_or_none()
    if work_order:
        return abort('Work order is already created.')

    work_order_service.save(WorkOrder(
        brief_id=brief_id,
        supplier_code=supplier_code,
        data={
            "created_by": current_user.email_address
        }
    ))

    audit_service.log_audit_event(
        audit_type=audit_types.create_work_order,
        user=current_user.email_address,
        data={
            'briefId': brief.id
        },
        db_object=brief)

    return jsonify(work_order=work_order), 200


@api.route('/brief/<int:brief_id>/ask-a-question', methods=['POST'])
@login_required
@role_required('supplier')
def supplier_asks_a_question(brief_id):
    """seller asks a question (role=supplier)
    ---
    tags:
        - brief
    definitions:
        BriefAwarded:
            type: object
            properties:
                awardedSupplier:
                    type: string
    responses:
        200:
            description: Brief awarded successfully.
            schema:
                $ref: '#/definitions/BriefAwarded'
        400:
            description: Bad request.
        403:
            description: Unauthorised to award brief to seller.
        500:
            description: Unexpected error.
    """
    brief = briefs.get(brief_id)
    if not brief:
        return not_found('opportunity {} not found'.format(brief_id))

    if brief.withdrawn_at:
        return abort('opportunity {} is withdrawn'.format(brief_id))

    now = pendulum.now('Australia/Canberra')
    if not brief.published_at:
        return abort('opportunity is not published')

    if not brief.questions_closed_at or brief.questions_closed_at <= now:
        return abort('question deadline has passed')

    user_status = BriefUserStatus(brief, current_user)
    if not user_status.is_invited():
        return forbidden('only invited sellers can ask questions')

    data = get_json_from_request()
    question = data.get('question')
    if not question:
        return abort('Question is required.')

    brief_question = brief_question_service.save(BriefQuestion(
        brief_id=brief_id,
        supplier_code=current_user.supplier_code,
        data={
            "created_by": current_user.email_address,
            "question": question
        }
    ))

    audit_service.log_audit_event(
        audit_type=audit_types.create_brief_question,
        user=current_user.email_address,
        data={
            'briefId': brief.id
        },
        db_object=brief)

    supplier = suppliers.find(code=current_user.supplier_code).one_or_none()

    send_brief_clarification_to_buyer(brief, brief_question, supplier)
    send_brief_clarification_to_seller(brief, brief_question, current_user.email_address)

    publish_tasks.brief_question.delay(
        publish_tasks.compress_brief_question(brief_question),
        'created'
    )

    return jsonify(success=True), 200
