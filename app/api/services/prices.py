from flask_login import current_user
from app.api.helpers import Service
from app import db
from app.models import ServiceTypePrice, Region
from .audit import AuditService, AuditTypes


class PricesService(Service):
    __model__ = ServiceTypePrice

    def __init__(self, *args, **kwargs):
        super(PricesService, self).__init__(*args, **kwargs)
        self.audit = AuditService()

    def get_prices(self, code, service_type_id, category_id, date):
        prices = db.session.query(ServiceTypePrice)\
            .join(ServiceTypePrice.region)\
            .filter(ServiceTypePrice.supplier_code == code,
                    ServiceTypePrice.service_type_id == service_type_id,
                    ServiceTypePrice.sub_service_id == category_id,
                    ServiceTypePrice.is_current_price(date))\
            .distinct(Region.state, Region.name, ServiceTypePrice.supplier_code, ServiceTypePrice.service_type_id,
                      ServiceTypePrice.sub_service_id, ServiceTypePrice.region_id)\
            .order_by(Region.state, Region.name, ServiceTypePrice.supplier_code.desc(),
                      ServiceTypePrice.service_type_id.desc(), ServiceTypePrice.sub_service_id.desc(),
                      ServiceTypePrice.region_id.desc(), ServiceTypePrice.updated_at.desc())\
            .all()

        return [p.serializable for p in prices]

    def add_price(self, existing_price, date_from, date_to, price):
        new_price = self.__model__(
            supplier_code=existing_price.supplier_code,
            service_type_id=existing_price.service_type_id,
            sub_service_id=existing_price.sub_service_id,
            region_id=existing_price.region.id,
            service_type_price_ceiling_id=existing_price.service_type_price_ceiling.id,
            date_from=date_from,
            date_to=date_to,
            price=price
        )

        db.session.add(new_price)
        db.session.commit()

        self.audit.create(audit_type=AuditTypes.update_price, user=current_user.id, data={}, db_object=new_price)
        return new_price
