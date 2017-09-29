from app import db
from app.models import AuditEvent, AuditTypes, Supplier


def get_supplier(code):
    return Supplier.query.filter(
        Supplier.code == code,
        Supplier.status != 'deleted'
    ).first()


def valid_supplier(user):
    return False if user.role is not 'supplier' or user.supplier_code is None else True


def update_supplier_details(supplier_code, **kwargs):
    """
        Update a supplier. Looks user up in DB, and updates where necessary.
    """

    if supplier_code is None:
        raise ValueError("supplier_code was not provided in kwargs to update supplier function")

    supplier = Supplier.query.filter(Supplier.code == supplier_code).first()

    if supplier is None:
        raise ValueError("Unable to modify supplier. supplier with code {} does not exist".format(supplier_code))

    ignore_fields_for_supplier_update = ['case_studies', 'case_study_ids', 'domains', 'extraLinks',
                                         'extra_links', 'frameworks', 'prices', 'products', 'signed_agreements']

    for key, value in kwargs.items():
        if key in ignore_fields_for_supplier_update:
            kwargs.pop(key)

    kwargs = revert_flattened_supplier_json(kwargs)

    supplier.update_from_json(kwargs)

    audit = AuditEvent(
        audit_type=AuditTypes.supplier_update,
        user=None,
        data={
            'supplier': supplier.code,
            'update': kwargs
        },
        db_object=supplier
    )

    db.session.add(supplier)
    db.session.add(audit)

    db.session.commit()

    return supplier


def flatten_supplier(supplier):
    addresses = supplier.get('addresses', None)
    contacts = supplier.get('contacts', None)

    if addresses is not None and len(addresses) > 0:
        for k, v in addresses[0].items():
            if k != 'id':
                supplier['address_'+k] = v

    if contacts is not None and len(contacts) > 0:
        for k, v in contacts[0].items():
            if k != 'id':
                supplier['contact_'+k] = v

    supplier.pop('addresses', None)
    supplier.pop('address', None)
    supplier.pop('contacts', None)

    return supplier


def revert_flattened_supplier_json(supplier):
    supplier['addresses'] = [{}]
    supplier.get('addresses')[0]['country'] = supplier.get('address_country', None)
    supplier.get('addresses')[0]['address_line'] = supplier.get('address_address_line', None)
    supplier.get('addresses')[0]['country'] = supplier.get('address_country', None)
    supplier.get('addresses')[0]['postal_code'] = supplier.get('address_postal_code', None)
    supplier.get('addresses')[0]['state'] = supplier.get('address_state', None)
    supplier.get('addresses')[0]['suburb'] = supplier.get('address_suburb', None)
    supplier.get('addresses')[0]['supplier_code'] = supplier.get('supplier_code', None)

    supplier['contacts'] = [{}]
    supplier.get('contacts')[0]['contactFor'] = supplier.get('contact_contactFor', None)
    supplier.get('contacts')[0]['contact_for'] = supplier.get('contact_contact_for', None)
    supplier.get('contacts')[0]['email'] = supplier.get('contact_email', None)
    supplier.get('contacts')[0]['fax'] = supplier.get('contact_fax', None)
    supplier.get('contacts')[0]['name'] = supplier.get('contact_name', None)
    supplier.get('contacts')[0]['phone'] = supplier.get('contact_phone', None)

    return supplier
