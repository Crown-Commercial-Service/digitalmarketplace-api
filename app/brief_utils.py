# coding: utf-8

import json
import copy
import rollbar
from flask import abort, request
from app.api.services import suppliers, users
from .models import Service
from .service_utils import filter_services
from .validation import get_validation_errors, get_required_fields


def clean_brief_data(brief):
    __del_seller_email_list(brief.data)
    __del_seller_email(brief.data)
    __del_lds(brief)
    __del_own_preference(brief)


def add_defaults(brief_json):
    if brief_json.get('lot') != 'training':
        return

    brief_json['evaluationTypeSellerSubmissions'] = ['Written proposal', 'Project costs', u'Trainer r\u00E9sum\u00E9s']


def validate_brief_data(brief, enforce_required=True, required_fields=None):
    required_fields = determine_required_fields(brief=brief,
                                                enforce_required=enforce_required,
                                                required_fields=required_fields)

    errs = get_validation_errors(
        'briefs-{}-{}'.format(brief.framework.slug, brief.lot.slug),
        brief.data,
        enforce_required=enforce_required,
        required_fields=required_fields
    )
    criteria_weighting_keys = ['technicalWeighting', 'culturalWeighting', 'priceWeighting']
    # Only check total if all weightings are set
    if not errs and all(key in brief.data for key in criteria_weighting_keys):
        criteria_weightings = sum(brief.data[key] for key in criteria_weighting_keys)
        if criteria_weightings != 100:
            for key in criteria_weighting_keys:
                errs[key] = 'total_should_be_100'

    seller_email_error = check_seller_emails(brief.data, errs)
    if seller_email_error:
        for k, value in seller_email_error.iteritems():
            errs[k] = value

    lds_errors = check_lds(brief, required_fields)
    for lds_error in lds_errors:
        for k, value in lds_error.iteritems():
            errs[k] = value

    training_method_error = check_training_method(brief)
    if training_method_error:
        for k, value in training_method_error.iteritems():
            errs[k] = value

    if errs:
        rollbar.report_message(json.dumps(errs), 'error', request)
        abort(400, errs)


def get_supplier_service_eligible_for_brief(supplier, brief):
    services = filter_services(
        framework_slugs=[brief.framework.slug],
        statuses=["published"],
        lot_slug=brief.lot.slug,
        role=brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    )

    services = services.filter(Service.supplier_code == supplier.code)

    return services.first()


def check_seller_emails(brief_data, errs):
    seller_selector = brief_data.get('sellerSelector', None)
    if seller_selector == 'allSellers':
        return None

    seller_email_key = None
    emails_to_check = []
    # empty checking
    if seller_selector == 'oneSeller':
        seller_email_key = 'sellerEmail'
        if not brief_data.get(seller_email_key, None):
            return {seller_email_key: 'answer_required'}

        emails_to_check = [brief_data[seller_email_key]]
    elif seller_selector == 'someSellers':
        seller_email_key = 'sellerEmailList'
        emails_to_check = brief_data.get(seller_email_key, [])
        if not emails_to_check:
            return {seller_email_key: 'answer_required'}

    if seller_email_key in errs:
        return None

    # if they exist in db
    error = {seller_email_key: 'email_not_found'}

    if any(emails_to_check):
        # Buyers may enter emails with upper case
        seller_emails = [email.lower() for email in emails_to_check]
        found_users = users.get_sellers_by_email(seller_emails)

        if len(found_users) != len(emails_to_check):
            # Check to see if contact emails were used
            found_user_emails = [user.email_address.lower() for user in found_users]
            contact_emails_to_check = [email.lower() for email in seller_emails if email not in found_user_emails]
            found_suppliers = [
                f.data.get('contact_email').lower()
                for f in suppliers.get_suppliers_by_contact_email(contact_emails_to_check)
            ]
            diff = set(seller_emails) - set(found_user_emails + found_suppliers)
            if len(diff) > 0:
                error[seller_email_key] = str(error[seller_email_key]) + '~' + ','.join(diff)
                return error

    return None


# This function is only applicable for training briefs.
# It is used to determine the required fields based on what is selected in what_training
# and what is selected in the proposal fields.
# This also takes into account where the user is. i.e. section, page or brief
def determine_required_fields(brief, section=None, enforce_required=True, required_fields=None):
    optional_fields = []

    if section:
        required_fields = copy.deepcopy(section['required'])
        optional_fields = copy.deepcopy(section['optional'])
    elif required_fields is not None:
        pass
    else:
        required_fields = copy.deepcopy(get_required_fields(brief))

    if brief.lot.name != 'Training':
        return required_fields

    brief_data = brief.data
    for wt in [wt.lower() for wt in brief_data.get('whatTraining', [])]:
        fields = __get_lds_fields_from_what_training(wt)
        if wt == 'other':
            for field in fields:
                if (enforce_required is True or
                        (enforce_required is False and
                         field in required_fields or
                         field in optional_fields)):
                    required_fields.append(field)
        else:
            proposal_field = fields[0]
            unit_field = fields[1]
            training_need_field = fields[2]

            if (enforce_required is True or
                    (enforce_required is False and
                     (proposal_field in required_fields or
                      proposal_field in optional_fields))):
                lds_radio = brief_data.get(proposal_field, None)
                if lds_radio == 'ldsUnits':
                    required_fields.append(unit_field)
                elif lds_radio == 'specify':
                    required_fields.append(training_need_field)
                else:
                    required_fields.append(proposal_field)

    return required_fields


def __del_seller_email(brief_data):
    seller_selector = brief_data.get('sellerSelector', None)
    seller_email = 'sellerEmail'
    if seller_email in brief_data:
        if (seller_selector == 'someSellers' or seller_selector == 'allSellers'):
            del brief_data[seller_email]


def __del_seller_email_list(brief_data):
    seller_selector = brief_data.get('sellerSelector', None)
    seller_email_list_key = 'sellerEmailList'
    if seller_email_list_key in brief_data:
        if (seller_selector == 'oneSeller' or seller_selector == 'allSellers'):
            del brief_data[seller_email_list_key]


def __del_own_preference(brief):
    if brief.lot.name != 'Training':
        return

    brief_data = brief.data
    approach_selector = brief_data.get('approachSelector', None)
    if not approach_selector:
        return

    if approach_selector == 'open':
        if 'trainingApproachOwn' in brief_data:
            del brief_data['trainingApproachOwn']


def check_training_method(brief):
    if brief.lot.name != 'Training':
        return

    brief_data = brief.data
    approach_selector = brief_data.get('approachSelector', None)
    if not approach_selector:
        return

    if approach_selector == 'ownPreference':
        if ('trainingApproachOwn' not in brief_data or
                brief_data.get('trainingApproachOwn', None) == ''):
            return {'trainingApproachOwn': 'answer_required'}


def check_lds(brief, required_fields):
    result = []
    brief_data = brief.data
    if brief.lot.name != 'Training':
        return result

    for what_training in [wt.lower() for wt in brief_data.get('whatTraining', [])]:
        lds_field = __get_lds_fields_from_what_training(what_training)
        if what_training == 'other':
            for f in lds_field:
                if brief_data.get(f, None) is None and f in required_fields:
                    result.append({f: 'answer_required'})
        else:
            proposal_field = lds_field[0]
            unit_field = lds_field[1]
            training_need_field = lds_field[2]

            lds_radio = brief_data.get(proposal_field, None)
            if lds_radio:
                if lds_radio == 'ldsUnits':
                    if brief_data.get(unit_field, None) is None and unit_field in required_fields:
                        result.append({unit_field: 'answer_required'})
                elif lds_radio == 'specify':
                    if (brief_data.get(training_need_field, None) is None and
                            training_need_field in required_fields):
                        result.append({training_need_field: 'answer_required'})
            elif proposal_field in required_fields:
                result.append({proposal_field: 'answer_required'})

    return result


def __del_lds(brief):
    brief_data = brief.data
    if brief.lot.name != 'Training':
        return

    lds_values = [
        'digital foundations',
        'agile delivery',
        'user research',
        'content design',
        'other'
    ]
    what_trainings = [wt.lower() for wt in brief_data.get('whatTraining', [])]
    for lds_value in lds_values:
        if lds_value not in what_trainings:
            lds_field = __get_lds_fields_from_what_training(lds_value)
            for f in lds_field:
                if f in brief_data:
                    del brief_data[f]

    for what_training in what_trainings:
        if what_training == 'other':
            continue

        lds_field = __get_lds_fields_from_what_training(what_training)
        proposal_field = lds_field[0]
        unit_field = lds_field[1]
        training_need_field = lds_field[2]

        lds_radio = brief_data.get(proposal_field, None)
        if lds_radio:
            if lds_radio == 'sellerProposal':
                if training_need_field in brief_data:
                    del brief_data[training_need_field]
                if unit_field in brief_data:
                    del brief_data[unit_field]
            elif lds_radio == 'ldsUnits':
                if training_need_field in brief_data:
                    del brief_data[training_need_field]
            elif lds_radio == 'specify':
                if unit_field in brief_data:
                    del brief_data[unit_field]


def __get_lds_fields_from_what_training(what_training):
    lds_fields = {
        'digital foundations': [
            'ldsDigitalFoundationProposalOrLds',
            'ldsDigitalFoundationUnits',
            'ldsDigitalFoundationTrainingNeeds'
        ],
        'agile delivery': [
            'ldsAgileDeliveryProposalOrLds',
            'ldsAgileDeliveryUnits',
            'ldsAgileDeliveryTrainingNeeds'
        ],
        'user research': [
            'ldsUserResearchProposalOrLds',
            'ldsUserResearchUnits',
            'ldsUserResearchTrainingNeeds'
        ],
        'content design': [
            'ldsContentDesignProposalOrLds',
            'ldsContentDesignUnits',
            'ldsContentDesignTrainingNeeds'
        ],
        'other': [
            'trainingDetailType',
            'trainingDetailCover'
        ]
    }
    for k, v in lds_fields.iteritems():
        if what_training.lower() == k:
            return v
    return None
