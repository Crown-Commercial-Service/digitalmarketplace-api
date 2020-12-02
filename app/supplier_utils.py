import inspect
from typing import Union

from flask import abort, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import lazyload

from dmapiclient.audit import AuditTypes

from .validation import validate_supplier_json_or_400, validate_new_supplier_json_or_400, get_validation_errors
from .utils import get_json_from_request, json_has_matching_id, json_has_required_keys, drop_foreign_fields
from .models.main import AuditEvent, Supplier, SupplierFramework, Framework
from . import supplier_constants


def validate_and_return_supplier_request(supplier_id=None):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['suppliers'])
    json_has_required_keys(json_payload['suppliers'], ['contactInformation'])

    # remove unnecessary fields
    json_payload['suppliers'] = drop_foreign_fields(json_payload['suppliers'], ['links'], recurse=True)

    if supplier_id:
        validate_supplier_json_or_400(json_payload['suppliers'])
        json_has_matching_id(json_payload['suppliers'], supplier_id)
    else:
        validate_new_supplier_json_or_400(json_payload['suppliers'])

    return json_payload['suppliers']


def validate_agreement_details_data(agreement_details, enforce_required=True, required_fields=None):
    errs = get_validation_errors(
        'agreement-details',
        agreement_details,
        enforce_required=enforce_required,
        required_fields=required_fields
    )

    if errs:
        abort(400, errs)


def check_supplier_role(role, supplier_id):
    if role == 'supplier' and not supplier_id:
        abort(400, "'supplierId' is required for users with 'supplier' role")
    elif role != 'supplier' and supplier_id:
        abort(400, "'supplierId' is only valid for users with 'supplier' role, not '{}'".format(role))


def company_details_confirmed_if_required_for_framework(framework_slug, supplier_framework):
    return (
        supplier_framework.supplier.company_details_confirmed
        if framework_slug == 'g-cloud-10' else
        supplier_framework.application_company_details_confirmed
    )


def update_open_declarations_with_company_details(db, supplier_id, updater_json, specific_framework_slug=None):
    """Expected to be called within a view"""
    open_supplier_frameworks_query = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier_id,
        SupplierFramework.framework.has(Framework.status == 'open'),
    )

    if specific_framework_slug:
        open_supplier_frameworks_query = open_supplier_frameworks_query.filter(
            SupplierFramework.framework.has(Framework.slug == specific_framework_slug),
        )

    # We need to ensure that SupplierFramework and Framework haven't changed during this transaction, so grab
    # the affected rows with a for update lock.
    try:
        # This query invokes an autoflush. If there is something wrong with an object which has been staged for commit,
        # such as a supplier with a bad update, this kicks an Integrity error which we need to catch and handle.
        open_supplier_frameworks = open_supplier_frameworks_query.options(lazyload('*')).with_for_update().all()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    if not open_supplier_frameworks:
        return

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    # Update the open framework application(s) with latest company details.
    for open_supplier_framework in open_supplier_frameworks:
        company_details = {
            supplier_constants.KEY_TRADING_NAME: supplier.name,
            supplier_constants.KEY_REGISTERED_NAME: supplier.registered_name,
            supplier_constants.KEY_REGISTRATION_NUMBER: (
                supplier.companies_house_number or supplier.other_company_registration_number
            ),
            supplier_constants.KEY_DUNS_NUMBER: supplier.duns_number,
            supplier_constants.KEY_TRADING_STATUS: supplier.trading_status,
            supplier_constants.KEY_ORGANISATION_SIZE: supplier.organisation_size,
            supplier_constants.KEY_REGISTRATION_COUNTRY: supplier.registration_country,
            supplier_constants.KEY_REGISTRATION_BUILDING: supplier.contact_information[0].address1,
            supplier_constants.KEY_REGISTRATION_TOWN: supplier.contact_information[0].city,
            supplier_constants.KEY_REGISTRATION_POSTCODE: supplier.contact_information[0].postcode,
        }

        company_details_without_nones = {k: v for k, v in company_details.items() if v is not None}

        open_supplier_framework.declaration = {
            **open_supplier_framework.declaration,
            **company_details_without_nones
        }

        db.session.add(open_supplier_framework)

        calling_function = inspect.stack()[1].function
        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.answer_selection_questions,
                db_object=open_supplier_framework,
                user=f"{updater_json['updated_by']} - (triggered from {calling_function})",
                data={
                    "update": company_details,
                    "supplierId": supplier.supplier_id,
                },
            )
        )


def is_g12_recovery_supplier(supplier_id: Union[str, int]) -> bool:
    supplier_ids_string = current_app.config.get('DM_G12_RECOVERY_SUPPLIER_IDS') or ''

    try:
        supplier_ids = [int(s) for s in supplier_ids_string.split(sep=',')]
    except AttributeError as e:
        current_app.logger.error("DM_G12_RECOVERY_SUPPLIER_IDS not a string", extra={'error': str(e)})
        return False
    except ValueError as e:
        current_app.logger.error("DM_G12_RECOVERY_SUPPLIER_IDS not a list of supplier IDs", extra={'error': str(e)})
        return False

    return int(supplier_id) in supplier_ids
