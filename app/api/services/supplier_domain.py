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

    def set_supplier_domain_status(self, supplier_id, domain_id, status, price_status, do_commit=True):
        existing = self.filter(
            SupplierDomain.domain_id == domain_id,
            SupplierDomain.supplier_id == supplier_id
        ).one_or_none()
        if existing:
            existing.status = status
            existing.price_status = price_status
            return self.save(existing, do_commit)
        else:
            supplier_domain = SupplierDomain(
                domain_id=domain_id,
                supplier_id=supplier_id,
                status=status,
                price_status=price_status
            )
            return self.save(supplier_domain, do_commit)
