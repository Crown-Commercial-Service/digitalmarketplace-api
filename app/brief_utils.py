import json

import rollbar
from flask import abort, request

from .models import Service
from .service_utils import filter_services
from .validation import get_validation_errors


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
