from app import db
from app.api.helpers import Service
from app.models import (Supplier, Domain, SupplierDomain, Assessment)


class SupplierDomainService(Service):
    __model__ = SupplierDomain

    def __init__(self, *args, **kwargs):
        super(SupplierDomainService, self).__init__(*args, **kwargs)

    def get_supplier_domains(self, supplier_code):
        result = (
            db
            .session
            .query(
                SupplierDomain.id,
                SupplierDomain.status,
                Domain.name.label('service'),
                Domain.id.label('service_id'),
                Assessment.active.label('active_assessment')
            )
            .join(Supplier)
            .join(Domain)
            .outerjoin(Assessment)
            .filter(Supplier.code == supplier_code)
            .order_by(Domain.name)
            .all()
        )

        return [r._asdict() for r in result]
