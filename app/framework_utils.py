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
