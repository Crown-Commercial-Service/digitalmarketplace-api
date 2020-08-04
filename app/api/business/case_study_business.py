from app.api.services import (
    case_study
)


def get_approved_case_studies(supplier_code, domain_id):
    case_studies = case_study.get_approved_case_studies_by_supplier_code(supplier_code, domain_id)
    return case_studies
