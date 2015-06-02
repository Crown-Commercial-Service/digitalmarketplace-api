from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError

from .. import main
from ... import db
from ...models import Supplier, ContactInformation, Activity
from ...validation import (
    validate_supplier_json_or_400,
    validate_contact_information_json_or_400
)
from ...utils import pagination_links, drop_foreign_fields, \
    get_json_from_request, json_has_required_keys, json_has_matching_id


@main.route('/suppliers', methods=['GET'])
def list_suppliers():
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    prefix = request.args.get('prefix', '')

    suppliers = Supplier.query.order_by(Supplier.name)

    if prefix:
        if prefix == 'other':
            suppliers = suppliers.filter(
                Supplier.name.op('~')('^[^A-Za-z]'))
        else:
            # case insensitive LIKE comparison for matching supplier names
            suppliers = suppliers.filter(
                Supplier.name.ilike(prefix + '%'))

    suppliers = suppliers.paginate(
        page=page,
        per_page=current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'],
    )

    if not suppliers.items:
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


# Route to insert new Suppliers, not update existing ones
@main.route('/suppliers/<int:supplier_id>', methods=['PUT'])
def import_supplier(supplier_id):
    supplier_data = get_json_from_request()

    json_has_required_keys(
        supplier_data,
        ['suppliers']
    )

    supplier_data = supplier_data['suppliers']
    supplier_data = drop_foreign_fields(supplier_data, ['links'])

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

    # Check that `supplier_id` matches the JSON-supplied `id`
    json_has_matching_id(supplier_data, supplier_id)

    supplier_data = drop_foreign_fields(
        supplier_data,
        ['contactInformation']
    )

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_data['id']
    ).first()

    if supplier is None:
        supplier = Supplier(supplier_id=supplier_data['id'])

    # if a supplier was found, remove all contact information
    else:
        for contact in supplier.contact_information:
            db.session.delete(contact)

    supplier.update(supplier_data)

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
        abort(400, "Database Error: {0}".format(e))

    return jsonify(suppliers=supplier.serialize()), 201


@main.route('/suppliers/<int:supplier_id>', methods=['POST'])
def update_supplier(supplier_id):
    request_data = get_json_from_request()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first()

    if supplier is None:
        abort(404, "supplier_id '%d' not found" % supplier_id)

    json_has_required_keys(request_data, ['suppliers'])

    supplier_data = supplier.serialize()
    supplier_data.update(request_data['suppliers'])
    supplier_data = drop_foreign_fields(
        supplier_data,
        ['links', 'contactInformation']
    )

    validate_supplier_json_or_400(supplier_data)
    json_has_matching_id(supplier_data, supplier_id)

    supplier.update(supplier_data)

    db.session.add(supplier)

    try:
        db.session.flush()
        activity = Activity(verb=u'update', object=supplier)
        db.session.add(activity)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(suppliers=supplier.serialize())


@main.route(
    '/suppliers/<int:supplier_id>/contact-information/<int:contact_id>',
    methods=['POST'])
def update_contact_information(supplier_id, contact_id):
    request_data = get_json_from_request()

    contact = ContactInformation.query.filter(
        ContactInformation.id == contact_id,
        ContactInformation.supplier_id == supplier_id,
    ).first()

    if contact is None:
        abort(404, "contact_id '%d' not found" % contact_id)

    json_has_required_keys(request_data, ['contactInformation'])

    contact_data = contact.serialize()
    contact_data.update(request_data['contactInformation'])
    contact_data = drop_foreign_fields(
        contact_data,
        ['links']
    )

    validate_contact_information_json_or_400(contact_data)
    json_has_matching_id(contact_data, contact_id)

    contact.update(contact_data)

    db.session.add(contact)

    try:
        db.session.flush()
        activity = Activity(verb=u'update', object=contact)
        db.session.add(activity)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(contactInformation=contact.serialize())
