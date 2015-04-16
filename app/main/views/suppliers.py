from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError

from .. import main
from ... import db
from ...models import Supplier, ContactInformation
from ...validation import validate_supplier_json_or_400
from ...utils import pagination_links, drop_foreign_fields, \
    get_json_from_request, json_has_required_keys


@main.route('/suppliers', methods=['GET'])
def list_suppliers():

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    prefix = request.args.get('prefix', '')

    suppliers = Supplier.query

    if prefix:
        # case insensitive LIKE comparison for matching supplier names
        suppliers = suppliers.filter(
            Supplier.name.ilike(prefix + '%'))

    suppliers = suppliers.paginate(
        page=page,
        per_page=current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'],
        error_out=False,
    )

    if not suppliers.items:
        if page > 1:
            abort(404, "Page number out of range")
        else:
            abort(404, "No suppliers found for '{0}'".format(prefix))

    return jsonify(
        suppliers=[supplier.serialize() for supplier in suppliers.items],
        links=pagination_links(
            suppliers,
            '.list_suppliers',
            request.args
        ))


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=supplier.serialize())


# Route to insert new Suppliers
@main.route('/suppliers', methods=['POST'])
def import_supplier():

    supplier_data = get_json_from_request()

    json_has_required_keys(
        supplier_data,
        ['suppliers']
    )

    supplier_data = supplier_data['suppliers']

    json_has_required_keys(
        supplier_data,
        ['id', 'name', 'contactInformation']
    )

    contact_informations_data = supplier_data['contactInformation']

    for contact_information_data in contact_informations_data:
        json_has_required_keys(
            contact_information_data,
            ['contactName', 'email', 'postcode']
        )

    validate_supplier_json_or_400(supplier_data)

    supplier_data = drop_foreign_fields(
        supplier_data,
        ['contactInformation']
    )

    supplier = Supplier(supplier_id=supplier_data['id'])
    supplier.name = supplier_data.get('name', None)
    supplier.description = supplier_data.get('description', None)
    supplier.contact_information = []
    supplier.duns_number = supplier_data.get('dunsNumber', None)
    supplier.esourcing_id = supplier_data.get('eSourcingId', None)
    supplier.clients = supplier_data.get('clients', None)

    for contact_information_data in contact_informations_data:

        contact_information = ContactInformation()

        contact_information.contact_name = \
            contact_information_data.get('contactName', None)
        contact_information.phone_number = \
            contact_information_data.get('phoneNumber', None)
        contact_information.email = \
            contact_information_data.get('email', None)
        contact_information.website = \
            contact_information_data.get('website', None)
        contact_information.address1 = \
            contact_information_data.get('address1', None)
        contact_information.address2 = \
            contact_information_data.get('address2', None)
        contact_information.city = \
            contact_information_data.get('city', None)
        contact_information.country = \
            contact_information_data.get('country', None)
        contact_information.postcode = \
            contact_information_data.get('postcode', None)

        supplier.contact_information.append(contact_information)

    db.session.add(supplier)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e.message))

    return "", 201
