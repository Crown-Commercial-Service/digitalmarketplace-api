import json

import rollbar
from flask import abort, request
from app.api.services import users
from .models import Service
from .service_utils import filter_services
from .validation import get_validation_errors


def clean_brief_data(brief):
    __del_seller_email_list(brief.data)
    __del_seller_email(brief.data)


def validate_brief_data(brief, enforce_required=True, required_fields=None):
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
        found_emails = users.get_sellers_by_email(emails_to_check)
        if len(found_emails) != len(emails_to_check):
            return error

    return None


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
