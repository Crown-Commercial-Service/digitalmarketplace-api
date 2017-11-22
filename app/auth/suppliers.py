from app import db
from app.models import AuditEvent, AuditTypes, Supplier, ServiceTypePrice, ServiceSubType, ServiceType, ServiceCategory
from flask import jsonify
from itertools import groupby
from operator import itemgetter


def get_supplier(code):
    supplier = Supplier.query.filter(
        Supplier.code == code,
        Supplier.status != 'deleted'
    ).first_or_404()

    return jsonify(supplier.serializable), 200


def update_supplier(supplier_code, **kwargs):
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


def get_all_suppliers():
    suppliers = db.session.query(ServiceCategory.name.label('category_name'), Supplier.code, Supplier.name)\
        .select_from(Supplier)\
        .join(ServiceTypePrice, ServiceTypePrice.supplier_code == Supplier.code)\
        .join(ServiceType, ServiceType.id == ServiceTypePrice.service_type_id)\
        .join(ServiceCategory, ServiceCategory.id == ServiceType.category_id)\
        .group_by(ServiceCategory.name, Supplier.code, Supplier.name)\
        .order_by(ServiceCategory.name, Supplier.name)\
        .all()

    suppliers_json = [dict(category_name=s.category_name, name=s.name, code=s.code) for s in suppliers]

    result = []
    for key, group in groupby(suppliers_json, key=itemgetter('category_name')):
        result.append(dict(name=key, suppliers=list(remove('category_name', group))))

    return jsonify(categories=result), 200


def remove(key, group):
    for item in group:
        del item[key]
        yield item
