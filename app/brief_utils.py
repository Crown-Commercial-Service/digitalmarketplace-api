from flask import abort

from .validation import get_validation_errors


def validate_brief_data(brief, enforce_required=True, required_fields=None):
    errs = get_validation_errors(
        'briefs-{}-{}'.format(brief.framework.slug, brief.lot.slug),
        brief.data,
        enforce_required=enforce_required,
        required_fields=required_fields
    )

    if errs:
        abort(400, errs)
