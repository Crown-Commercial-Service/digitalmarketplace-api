import json
import mimetypes
import os
import botocore
import rollbar
import pendulum
from pendulum.parsing.exceptions import ParserError
from flask import Response, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import DataError

from app.api import api
from app.api.csv import generate_brief_responses_csv
from app.api.business.validators import SupplierValidator, RFXDataValidator, ATMDataValidator
from app.api.business.brief import BriefUserStatus
from app.api.business import supplier_business
from app.api.helpers import abort, forbidden, not_found, role_required, is_current_user_in_brief
from app.api.services import (audit_service,
                              brief_overview_service,
                              brief_responses_service,
                              briefs,
                              domain_service,
                              frameworks_service,
                              lots_service,
                              suppliers,
                              users)
from app.emails import (
    send_brief_response_received_email,
    render_email_template,
    send_seller_invited_to_rfx_email
)
from app.api.helpers import notify_team
from app.tasks import publish_tasks
from dmapiclient.audit import AuditTypes
from dmutils.file import s3_download_file, s3_upload_file_from_request

from ...models import (AuditEvent, Brief, BriefResponse, Framework, Supplier,
                       ValidationError, Lot, User, Domain, db)
from ...utils import get_json_from_request


def _can_do_brief_response(brief_id):
    try:
        brief = Brief.query.get(brief_id)
    except DataError:
        brief = None

    if brief is None:
        abort("Invalid brief ID '{}'".format(brief_id))

    if brief.status != 'live':
        abort("Brief must be live")

    if brief.framework.status != 'live':
        abort("Brief framework must be live")

    if not hasattr(current_user, 'role') or current_user.role != 'supplier':
        forbidden("Only supplier role users can respond to briefs")

    try:
        supplier = Supplier.query.filter(
            Supplier.code == current_user.supplier_code
        ).first()
    except DataError:
        supplier = None

    if not supplier:
        forbidden("Invalid supplier Code '{}'".format(current_user.supplier_code))

    validation_result = SupplierValidator(supplier).validate_all()
    if len(validation_result.errors) > 0:
        abort(validation_result.errors)

    def domain(email):
        return email.split('@')[-1]

    current_user_domain = domain(current_user.email_address) \
        if domain(current_user.email_address) not in current_app.config.get('GENERIC_EMAIL_DOMAINS') \
        else None

    rfx_lot = lots_service.find(slug='rfx').one_or_none()
    rfx_lot_id = rfx_lot.id if rfx_lot else None

    atm_lot = lots_service.find(slug='atm').one_or_none()
    atm_lot_id = atm_lot.id if atm_lot else None

    is_selected = False
    seller_selector = brief.data.get('sellerSelector', '')
    open_to = brief.data.get('openTo', '')
    brief_category = brief.data.get('sellerCategory', '')
    brief_domain = domain_service.get_by_name_or_id(int(brief_category)) if brief_category else None

    if brief.lot_id == rfx_lot_id:
        if str(current_user.supplier_code) in brief.data['sellers'].keys():
            is_selected = True

    elif brief.lot_id == atm_lot_id:
        if seller_selector == 'allSellers' and len(supplier.assessed_domains) > 0:
            is_selected = True
        elif seller_selector == 'someSellers' and open_to == 'category' and brief_domain and\
                                brief_domain.name in supplier.assessed_domains:
            is_selected = True

    else:
        if not seller_selector or seller_selector == 'allSellers':
            is_selected = True
        elif seller_selector == 'someSellers':
            seller_domain_list = [domain(x).lower() for x in brief.data['sellerEmailList']]
            if current_user.email_address in brief.data['sellerEmailList'] \
               or (current_user_domain and current_user_domain.lower() in seller_domain_list):
                is_selected = True
        elif seller_selector == 'oneSeller':
            if current_user.email_address.lower() == brief.data['sellerEmail'].lower() \
               or (current_user_domain and current_user_domain.lower() == domain(brief.data['sellerEmail'].lower())):
                is_selected = True
    if not is_selected:
        forbidden("Supplier not selected for this brief")

    if (len(supplier.frameworks) == 0 or
            'digital-marketplace' != supplier.frameworks[0].framework.slug):

        abort("Supplier does not have Digital Marketplace framework")

    if len(supplier.assessed_domains) == 0:
        abort("Supplier does not have at least one assessed domain")
    else:
        training_lot = lots_service.find(slug='training').one_or_none()
        if brief.lot_id == training_lot.id:
            if 'Training, Learning and Development' not in supplier.assessed_domains:
                abort("Supplier needs to be assessed in 'Training, Learning and Development'")

    lot = lots_service.first(slug='digital-professionals')
    if brief.lot_id == lot.id:
        # Check the supplier can respond to the category
        brief_category = brief.data.get('areaOfExpertise', None)
        if brief_category and brief_category not in supplier.assessed_domains:
            abort("Supplier needs to be assessed in '{}'".format(brief_category))
        # Check if there are more than 3 brief response already from this supplier when professional aka specialists
        brief_response_count = brief_responses_service.find(supplier_code=supplier.code,
                                                            brief_id=brief.id,
                                                            withdrawn_at=None).count()
        if (brief_response_count > 2):  # TODO magic number
            abort("There are already 3 brief responses for supplier '{}'".format(supplier.code))
    else:
        # Check if brief response already exists from this supplier when outcome for all other types
        if brief_responses_service.find(supplier_code=supplier.code,
                                        brief_id=brief.id,
                                        withdrawn_at=None).one_or_none():
            abort("Brief response already exists for supplier '{}'".format(supplier.code))

    return supplier, brief


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
        brief = briefs.create_brief(user, framework, lot)
    except Exception as e:
        rollbar.report_exc_info()
        return jsonify(message=e.message), 400

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


@api.route('/brief/atm', methods=['POST'])
@login_required
@role_required('buyer')
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
        brief = briefs.create_brief(user, framework, lot)
    except Exception as e:
        rollbar.report_exc_info()
        return jsonify(message=e.message), 400

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
    """Get brief
    ---
    tags:
        - brief
    parameters:
      - name: brief_id
        in: path
        type: number
        required: true
    responses:
        200:
            description: Brief retrieved successfully.
            schema:
                type: object
                properties:
                    brief:
                        type: object
                    brief_response_count:
                        type: number
                    invited_seller_count:
                        type: number
                    can_respond:
                        type: boolean
                    open_to_all:
                        type: boolean
                    is_brief_owner:
                        type: boolean
                    is_buyer:
                        type: boolean
                    has_responded:
                        type: boolean
                    has_chosen_brief_category:
                        type: boolean
                    is_assessed_for_category:
                        type: boolean
                    is_assessed_in_any_category:
                        type: boolean
                    is_approved_seller:
                        type: boolean
                    is_awaiting_application_assessment:
                        type: boolean
                    is_awaiting_domain_assessment:
                        type: boolean
                    has_been_assessed_for_brief:
                        type: boolean
                    open_to_category:
                        type: boolean
                    is_applicant:
                        type: boolean
                    is_recruiter:
                        type: boolean
                    domains:
                        type: array
                        items:
                            type: object
        403:
            description: Unauthorised to view brief.
        404:
            description: Brief not found.
        500:
            description: Unexpected error.
    """
    brief = briefs.find(id=brief_id).one_or_none()
    if not brief:
        not_found("No brief for id '%s' found" % (brief_id))

    user_role = current_user.role if hasattr(current_user, 'role') else None
    invited_sellers = brief.data['sellers'] if 'sellers' in brief.data else {}

    is_buyer = False
    is_brief_owner = False
    brief_user_ids = [user.id for user in brief.users]
    if user_role == 'buyer':
        is_buyer = True
        if current_user.id in brief_user_ids:
            is_brief_owner = True

    if brief.status == 'draft' and not is_brief_owner:
        return forbidden("Unauthorised to view brief")

    brief_response_count = len(brief_responses_service.get_brief_responses(brief_id, None))
    invited_seller_count = len(invited_sellers)
    open_to_all = brief.lot.slug == 'atm' and brief.data.get('openTo', '') == 'all'
    open_to_category = brief.lot.slug == 'atm' and brief.data.get('openTo', '') == 'category'
    is_applicant = user_role == 'applicant'

    # gather facts about the user's status against this brief
    user_status = BriefUserStatus(brief, current_user)
    has_chosen_brief_category = user_status.has_chosen_brief_category()
    is_assessed_for_category = user_status.is_assessed_for_category()
    is_assessed_in_any_category = user_status.is_assessed_in_any_category()
    is_awaiting_application_assessment = user_status.is_awaiting_application_assessment()
    is_awaiting_domain_assessment = user_status.is_awaiting_domain_assessment()
    has_been_assessed_for_brief = user_status.has_been_assessed_for_brief()
    is_recruiter_only = user_status.is_recruiter_only()
    is_approved_seller = user_status.is_approved_seller()
    can_respond = user_status.can_respond()
    has_responded = user_status.has_responded()

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
        brief.data['contactEmail'] = [user.email_address for user in brief.users][0]
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

    return jsonify(brief=brief.serialize(with_users=False, with_author=is_brief_owner),
                   brief_response_count=brief_response_count,
                   invited_seller_count=invited_seller_count,
                   can_respond=can_respond,
                   has_chosen_brief_category=has_chosen_brief_category,
                   is_assessed_for_category=is_assessed_for_category,
                   is_assessed_in_any_category=is_assessed_in_any_category,
                   is_approved_seller=is_approved_seller,
                   is_awaiting_application_assessment=is_awaiting_application_assessment,
                   is_awaiting_domain_assessment=is_awaiting_domain_assessment,
                   has_been_assessed_for_brief=has_been_assessed_for_brief,
                   open_to_all=open_to_all,
                   open_to_category=open_to_category,
                   is_brief_owner=is_brief_owner,
                   is_buyer=is_buyer,
                   is_applicant=is_applicant,
                   is_recruiter_only=is_recruiter_only,
                   has_responded=has_responded,
                   domains=domains)


@api.route('/brief/<int:brief_id>', methods=['PATCH'])
@login_required
@role_required('buyer')
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
        not_found("Invalid brief id '{}'".format(brief_id))

    if brief.status != 'draft':
        abort('Cannot edit a {} brief'.format(brief.status))

    if brief.lot.slug not in ['rfx', 'atm']:
        abort('Brief lot not supported for editing')

    if current_user.role == 'buyer':
        brief_user_ids = [user.id for user in brief.users]
        if current_user.id not in brief_user_ids:
            return forbidden('Unauthorised to update brief')

    data = get_json_from_request()

    publish = False
    if 'publish' in data and data['publish']:
        del data['publish']
        publish = True

    if brief.lot.slug == 'rfx':
        # validate the RFX JSON request data
        errors = RFXDataValidator(data).validate(publish=publish)
        if len(errors) > 0:
            abort(', '.join(errors))

    if brief.lot.slug == 'atm':
        # validate the ATM JSON request data
        errors = ATMDataValidator(data).validate(publish=publish)
        if len(errors) > 0:
            abort(', '.join(errors))

    if brief.lot.slug == 'rfx' and 'evaluationType' in data:
        if 'Written proposal' not in data['evaluationType']:
            data['proposalType'] = []
        if 'Response template' not in data['evaluationType']:
            data['responseTemplate'] = []

    if brief.lot.slug == 'rfx' and 'sellers' in data and len(data['sellers']) > 0:
        data['sellerSelector'] = 'someSellers' if len(data['sellers']) > 1 else 'oneSeller'

    data['areaOfExpertise'] = ''
    if brief.lot.slug == 'atm' and 'openTo' in data:
        if data['openTo'] == 'all':
            data['sellerSelector'] = 'allSellers'
            data['sellerCategory'] = ''
        elif data['openTo'] == 'category':
            data['sellerSelector'] = 'someSellers'
            brief_domain = (
                domain_service.get_by_name_or_id(int(data['sellerCategory'])) if data['sellerCategory'] else None
            )
            if brief_domain:
                data['areaOfExpertise'] = brief_domain.name

    previous_status = brief.status
    if publish:
        brief.publish(closed_at=data['closedAt'])
        if 'sellers' in brief.data and data['sellerSelector'] != 'allSellers':
            for seller_code, seller in brief.data['sellers'].iteritems():
                supplier = suppliers.get_supplier_by_code(seller_code)
                if brief.lot.slug == 'rfx':
                    send_seller_invited_to_rfx_email(brief, supplier)
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

    brief.data = data
    briefs.save_brief(brief)

    if publish:
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


@api.route('/brief/<int:brief_id>', methods=['DELETE'])
@login_required
@role_required('buyer')
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
        not_found("Invalid brief id '{}'".format(brief_id))

    if current_user.role == 'buyer':
        brief_user_ids = [user.id for user in brief.users]
        if current_user.id not in brief_user_ids:
            return forbidden('Unauthorised to delete brief')

    if brief.status != 'draft':
        abort('Cannot delete a {} brief'.format(brief.status))

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
        extra_data = {'audit_type': AuditTypes.delete_brief, 'briefId': brief.id, 'exception': e.message}
        rollbar.report_exc_info(extra_data=extra_data)

    return jsonify(message='Brief {} deleted'.format(brief_id)), 200


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
        not_found("Invalid brief id '{}'".format(brief_id))

    if current_user.role == 'buyer':
        brief_user_ids = [user.id for user in brief.users]
        if current_user.id not in brief_user_ids:
            return forbidden('Unauthorised to view brief')

    if not (brief.lot.slug == 'digital-professionals' or
            brief.lot.slug == 'training'):
        abort('Lot {} is not supported'.format(brief.lot.slug))

    sections = brief_overview_service.get_sections(brief)

    return jsonify(sections=sections, status=brief.status, title=brief.data['title']), 200


@api.route('/brief/<int:brief_id>/responses', methods=['GET'])
@login_required
def get_brief_responses(brief_id):
    """All brief responses (role=supplier,buyer)
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
      BriefResponses:
        properties:
          briefResponses:
            type: array
            items:
              id: BriefResponse
    responses:
      200:
        description: A list of brief responses
        schema:
          id: BriefResponses
      404:
        description: brief_id not found
    """
    brief = briefs.get(brief_id)
    if not brief:
        not_found("Invalid brief id '{}'".format(brief_id))

    if current_user.role == 'buyer':
        brief_user_ids = [user.id for user in brief.users]
        if current_user.id not in brief_user_ids:
            return forbidden("Unauthorised to view brief or brief does not exist")

    supplier_code = getattr(current_user, 'supplier_code', None)
    if current_user.role == 'supplier':
        validation_result = supplier_business.get_supplier_messages(supplier_code, True)
        if len(validation_result.errors) > 0:
            abort(validation_result.errors)
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

    if current_user.role == 'buyer' and brief.status != 'closed':
        brief_responses = []
    else:
        brief_responses = brief_responses_service.get_brief_responses(brief_id, supplier_code)

    return jsonify(brief=brief.serialize(with_users=False, with_author=False),
                   briefResponses=brief_responses)


@api.route('/brief/<int:brief_id>/respond/documents/<string:supplier_code>/<slug>', methods=['POST'])
@login_required
def upload_brief_response_file(brief_id, supplier_code, slug):
    supplier, brief = _can_do_brief_response(brief_id)
    return jsonify({"filename": s3_upload_file_from_request(request, slug,
                                                            os.path.join(brief.framework.slug, 'documents',
                                                                         'brief-' + str(brief_id),
                                                                         'supplier-' + str(supplier.code)))
                    })


@api.route('/brief/<int:brief_id>/attachments/<slug>', methods=['POST'])
@login_required
@role_required('buyer')
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
        not_found("Invalid brief id '{}'".format(brief_id))

    brief_user_ids = [user.id for user in brief.users]
    if current_user.id not in brief_user_ids:
        return forbidden('Unauthorised to update brief')

    return jsonify({"filename": s3_upload_file_from_request(request, slug,
                                                            os.path.join(brief.framework.slug, 'attachments',
                                                                         'brief-' + str(brief_id)))
                    })


@api.route('/brief/<int:brief_id>/respond/documents')
@login_required
@role_required('buyer')
def download_brief_responses(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    brief_user_ids = [user.id for user in brief.users]
    if current_user.id not in brief_user_ids:
        return forbidden("Unauthorised to view brief or brief does not exist")
    if brief.status != 'closed':
        return forbidden("You can only download documents for closed briefs")

    response = ('', 404)
    if brief.lot.slug in ['digital-professionals', 'training', 'rfx', 'atm']:
        try:
            file = s3_download_file(
                'brief-{}-resumes.zip'.format(brief_id),
                os.path.join(brief.framework.slug, 'archives', 'brief-{}'.format(brief_id))
            )
        except botocore.exceptions.ClientError as e:
            rollbar.report_exc_info()
            not_found("Brief documents not found for brief id '{}'".format(brief_id))

        response = Response(file, mimetype='application/zip')
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
    brief_user_ids = [user.id for user in brief.users]

    if (hasattr(current_user, 'role') and
        (current_user.role == 'buyer' or
            (current_user.role == 'supplier' and _can_do_brief_response(brief_id)))):
        file = s3_download_file(slug, os.path.join(brief.framework.slug, 'attachments',
                                                   'brief-' + str(brief_id)))
        mimetype = mimetypes.guess_type(slug)[0] or 'binary/octet-stream'
        return Response(file, mimetype=mimetype)
    else:
        return not_found('File not found')


@api.route('/brief/<int:brief_id>/respond/documents/<int:supplier_code>/<slug>', methods=['GET'])
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
        return forbidden("Unauthorised to view brief or brief does not exist")


@api.route('/brief/<int:brief_id>/respond', methods=["POST"])
@login_required
def post_brief_response(brief_id):

    brief_response_json = get_json_from_request()
    supplier, brief = _can_do_brief_response(brief_id)
    try:
        brief_response = BriefResponse(
            data=brief_response_json,
            supplier=supplier,
            brief=brief
        )

        brief_response.validate()
        db.session.add(brief_response)
        db.session.flush()

    except ValidationError as e:
        brief_response_json['brief_id'] = brief_id
        rollbar.report_exc_info(extra_data=brief_response_json)
        message = ""
        if 'essentialRequirements' in e.message and e.message['essentialRequirements'] == 'answer_required':
            message = "Essential requirements must be completed"
            del e.message['essentialRequirements']
        if 'attachedDocumentURL' in e.message:
            if e.message['attachedDocumentURL'] == 'answer_required':
                message = "Documents must be uploaded"
            if e.message['attachedDocumentURL'] == 'file_incorrect_format':
                message = "Uploaded documents are in the wrong format"
            del e.message['attachedDocumentURL']
        if 'criteria' in e.message and e.message['criteria'] == 'answer_required':
            message = "Criteria must be completed"
        if len(e.message) > 0:
            message += json.dumps(e.message)
        return jsonify(message=message), 400
    except Exception as e:
        brief_response_json['brief_id'] = brief_id
        rollbar.report_exc_info(extra_data=brief_response_json)
        return jsonify(message=e.message), 400

    try:
        send_brief_response_received_email(supplier, brief, brief_response)
    except Exception as e:
        brief_response_json['brief_id'] = brief_id
        rollbar.report_exc_info(extra_data=brief_response_json)

    audit_service.log_audit_event(
        audit_type=AuditTypes.create_brief_response,
        user=current_user.email_address,
        data={
            'briefResponseId': brief_response.id,
            'briefResponseJson': brief_response_json,
        },
        db_object=brief_response)

    publish_tasks.brief_response.delay(
        publish_tasks.compress_brief_response(brief_response),
        'submitted',
        user=current_user.email_address
    )
    return jsonify(briefResponses=brief_response.serialize()), 201


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

    return not_found('brief not found')
