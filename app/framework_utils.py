import re

from flask import abort
from .validation import get_validation_errors


def validate_framework_agreement_details_data(framework_agreement_details, enforce_required=True, required_fields=None):
    errs = get_validation_errors(
        'framework-agreement-details',
        framework_agreement_details,
        enforce_required=enforce_required,
        required_fields=required_fields
    )

    if errs:
        abort(400, errs)


def format_framework_integrity_error_message(error, json_framework):
    if 'violates check constraint "ck_framework_has_direct_award_or_further_competition"' in str(error):
        error_message = "At least one of `hasDirectAward` or `hasFurtherCompetition` must be True"

    elif 'duplicate key value violates unique constraint "ix_frameworks_slug"' in str(error):
        error_message = "Slug '{}' already in use".format(json_framework.get('slug', '<unknown slug>'))
    elif re.search('Not a [a-z]+? value:', str(error)):
        error_message = 'Invalid framework'
    else:
        error_message = format(error)

    return error_message
