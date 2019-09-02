from app import db
from app.api.helpers import Service
from sqlalchemy import func
from sqlalchemy.sql import text
from app.models import Address, Product, RecruiterInfo, Supplier, SupplierDomain, Domain


class SuppliersService(Service):
    __model__ = Supplier

    def __init__(self, *args, **kwargs):
        super(SuppliersService, self).__init__(*args, **kwargs)

    def get_unassessed(self):
        s = text(
            "select distinct "
            'd.id "domain_id",'
            'd.name "domain_name",'
            's.id "supplier_id",'
            's.code "supplier_code",'
            's.name "supplier_name",'
            's.data#>>(\'{pricing,"\'||d.name||\'",maxPrice}\')::text[] "supplier_price",'
            'u.supplier_last_logged_in,'
            'cs.id "case_study_id" '
            'from case_study cs '
            'inner join supplier s on s.code = cs.supplier_code '
            "inner join domain d on d.name = cs.data->>'service' "
            'inner join supplier_domain sd on sd.domain_id = d.id '
            '                                 and sd.supplier_id = s.id '
            "                                 and sd.status = 'unassessed'"
            'inner join ('
            '   select supplier_code, '
            '   max(logged_in_at) "supplier_last_logged_in" '
            '   from "user" '
            '   group by supplier_code'
            ') u on u.supplier_code = s.code '
            'where s.data#>>(\'{pricing,"\'||d.name||\'",maxPrice}\')::text[] is not null'
        )
        result = db.session.execute(s)
        return [dict(r) for r in result]

    def get_suppliers(self):
        subquery = (
            db
            .session
            .query(
                SupplierDomain.supplier_id,
                func.json_agg(
                    func.json_build_object(
                        'category', Domain.name,
                        'status', SupplierDomain.status,
                        'recruiterInfo', func.json_build_object(
                            'id', RecruiterInfo.id,
                            'activeCandidates', RecruiterInfo.active_candidates,
                            'databaseSize', RecruiterInfo.database_size,
                            'placedCandidates', RecruiterInfo.placed_candidates,
                            'margin', RecruiterInfo.margin,
                            'markup', RecruiterInfo.markup,
                        ).label('recruiters'),
                        'pricing', func.json_build_object(
                            'supplierPrice', Supplier.data['pricing'][Domain.name]['maxPrice'].astext.label('maxPrice'),
                            'priceStatus', SupplierDomain.price_status,
                            'priceMinimum', Domain.price_minimum,
                            'priceMaximum', Domain.price_maximum,
                            'criteriaNeeded', Domain.criteria_needed
                        )
                    )
                ).label('categories')
            )
            .join(Domain)
            .join(Supplier)
            .outerjoin(RecruiterInfo)
            .group_by(SupplierDomain.supplier_id)
            .subquery()
        )

        product_subquery = (
            db
            .session
            .query(
                Product.supplier_code,
                func.json_agg(
                    func.json_build_object(
                        'productName', Product.name,
                        'productSummary', Product.summary,
                        'productWebsite', Product.website,
                        'productPricingLink', Product.pricing
                    )
                ).label('products')
            )
            .group_by(Product.supplier_code)
            .subquery()
        )

        address_subquery = (
            db
            .session
            .query(
                Address.supplier_code,
                func.json_agg(
                    func.json_build_object(
                        'addressLine', Address.address_line,
                        'suburb', Address.suburb,
                        'state', Address.state,
                        'postalCode', Address.postal_code,
                    )
                ).label('addresses')
            )
            .group_by(Address.supplier_code)
            .subquery()
        )

        result = (
            db
            .session
            .query(
                Supplier.code,
                Supplier.name,
                Supplier.abn,
                Supplier.status,
                Supplier.creation_time.label('creationTime'),
                Supplier.data['seller_type']['sme'].astext.label('sme'),
                Supplier.website,
                Supplier.linkedin,
                Supplier.data['number_of_employees'].label('numberOfEmployees'),
                Supplier.data['seller_type']['start_up'].astext.label('startUp'),
                Supplier.data['seller_type']['nfp_social_enterprise'].astext.label('notForProfit'),
                Supplier.data['regional'],
                Supplier.data['travel'],
                Supplier.data['seller_type']['disability'].astext.label('disability'),
                Supplier.data['seller_type']['female_owned'].astext.label('femaleOwned'),
                Supplier.data['seller_type']['indigenous'].astext.label('indigenous'),
                Supplier.data['representative'],
                Supplier.data['email'],
                Supplier.data['phone'],
                Supplier.data['contact_name'].label('contactName'),
                Supplier.data['contact_email'].label('contactEmail'),
                Supplier.data['contact_phone'].label('contactPhone'),
                subquery.columns.categories,
                product_subquery.columns.products,
                address_subquery.columns.addresses,
            )
            .outerjoin(subquery, Supplier.id == subquery.columns.supplier_id)
            .outerjoin(product_subquery, Supplier.code == product_subquery.columns.supplier_code)
            .outerjoin(address_subquery, Supplier.code == address_subquery.columns.supplier_code)
            .order_by(Supplier.code)
            .all()
        )

        return [r._asdict() for r in result]
