from flask import abort

from .models import Service
from .validation import get_validation_errors
from .service_utils import filter_services
from .utils import index_object


def validate_brief_data(brief, enforce_required=True, required_fields=None):
    errors = get_validation_errors(
        'briefs-{}-{}'.format(brief.framework.slug, brief.lot.slug),
        brief.data,
        enforce_required=enforce_required,
        required_fields=required_fields
    )

    criteria_weighting_keys = ['technicalWeighting', 'culturalWeighting', 'priceWeighting']
    # socialWeighting is optional
    if 'socialWeighting' in brief.data and brief.data['socialWeighting'] >= 10:
        criteria_weighting_keys.append('socialWeighting')
    # Only check total if all weightings are set
    if not errors and all(key in brief.data for key in criteria_weighting_keys):
        criteria_weightings = sum(brief.data[key] for key in criteria_weighting_keys)
        if criteria_weightings != 100:
            for key in criteria_weighting_keys:
                errors[key] = 'total_should_be_100'

    if errors:
        abort(400, errors)


def get_supplier_service_eligible_for_brief(supplier, brief):
    services = filter_services(
        framework_slugs=[brief.framework.slug],
        statuses=["published"],
        lot_slug=brief.lot.slug,
        role=brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    )

    services = services.filter(Service.supplier_id == supplier.supplier_id)

    return services.first()


def index_brief(brief):
    if brief.status != 'draft':
        index_object(
            framework=brief.framework.slug,
            doc_type='briefs',
            object_id=brief.id,
            serialized_object=brief.serialize(),
        )
