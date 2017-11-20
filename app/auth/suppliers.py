from app import db
from app.models import AuditEvent, AuditTypes, Supplier, ServiceTypePrice, ServiceSubType, ServiceType
from flask import jsonify
from itertools import groupby


def get_supplier(code):
    supplier = Supplier.query.filter(
        Supplier.code == code,
        Supplier.status != 'deleted'
    ).first_or_404()

    return jsonify(user=supplier.serializable), 200


def valid_supplier(user):
    return False if user.role is not 'supplier' or user.supplier_code is None else True


def update_supplier_details(supplier_code, **kwargs):
    if supplier_code is None:
        raise ValueError("supplier_code was not provided in kwargs to update supplier function")

    supplier = Supplier.query.filter(Supplier.code == supplier_code).first()

    if supplier is None:
        raise ValueError("Unable to modify supplier. supplier with code {} does not exist".format(supplier_code))

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


def get_supplier_services(code):
    supplier = db.session.query(Supplier).filter(Supplier.code == code).first()

    services = db.session\
        .query(ServiceTypePrice.service_type_id,
               ServiceType.name, ServiceTypePrice.sub_service_id, ServiceSubType.name.label('sub_service_name'))\
        .join(ServiceType, ServiceTypePrice.service_type_id == ServiceType.id)\
        .outerjoin(ServiceSubType, ServiceTypePrice.sub_service_id == ServiceSubType.id)\
        .filter(ServiceTypePrice.supplier_code == code)\
        .group_by(ServiceTypePrice.service_type_id, ServiceType.name,
                  ServiceTypePrice.sub_service_id, ServiceSubType.name)\
        .order_by(ServiceType.name)\
        .all()

    result = []
    for key, group in groupby(services, key=lambda x: dict(id=x.service_type_id, name=x.name)):
        subcategories = [dict(id=s.sub_service_id, name=s.sub_service_name) for s in group]
        result.append(dict(key, subCategories=subcategories))

    supplier_json = supplier.serializable
    return jsonify(services=result,
                   supplier=dict(name=supplier_json['name'], abn=supplier_json['abn'],
                                 email=supplier_json.get('email', None),
                                 contact=supplier_json.get('representative', None)))
