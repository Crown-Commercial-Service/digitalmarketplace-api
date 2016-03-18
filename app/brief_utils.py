from flask import abort

from .models import Service
from .validation import get_validation_errors
from .service_utils import filter_services


def validate_brief_data(brief, enforce_required=True, required_fields=None):
    errs = get_validation_errors(
        'briefs-{}-{}'.format(brief.framework.slug, brief.lot.slug),
        brief.data,
        enforce_required=enforce_required,
        required_fields=required_fields
    )

    if errs:
        abort(400, errs)


def is_supplier_eligible_for_brief(supplier, brief):
    services = filter_services(
        framework_slugs=[brief.framework.slug],
        statuses=["published"],
        lot_slug=brief.lot.slug,
        location=brief.data["location"],
        role=brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    )

    services = services.filter(Service.supplier_id == supplier.supplier_id)

    return services.count() > 0
