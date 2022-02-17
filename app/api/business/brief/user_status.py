import pendulum

from app.api.business.agreement_business import has_signed_current_agreement
from app.api.business.validators import SupplierValidator
from app.api.services import (application_service, assessments,
                              brief_responses_service, domain_service,
                              evidence_service, lots_service,
                              signed_agreement_service, suppliers)


class BriefUserStatus(object):
    def __init__(self, brief, current_user):
        self.brief = brief
        self.current_user = current_user
        self.supplier = None
        self.supplier_code = None
        self.user_role = current_user.role if hasattr(current_user, 'role') else None
        self.brief_category = None
        self.brief_domain = None
        self.invited_sellers = {}
        if self.user_role == 'supplier' and hasattr(current_user, 'supplier_code'):
            self.supplier_code = current_user.supplier_code
            self.supplier = suppliers.get_supplier_by_code(self.supplier_code)
        if brief:
            self.brief_category = self.brief.data.get('sellerCategory', '')
            self.brief_domain = (
                domain_service.get_by_name_or_id(int(self.brief_category)) if self.brief_category else None
            )
            self.invited_sellers = self.brief.data['sellers'] if 'sellers' in self.brief.data else {}

    def is_approved_seller(self):
        if self.supplier:
            return True
        return False

    def is_recruiter_only(self):
        if self.supplier and self.supplier.is_recruiter and 'recruiter' in self.supplier.data and\
           self.supplier.data['recruiter'] == 'yes':
            return True
        return False

    def is_assessed_in_any_category(self):
        if self.supplier and len(self.supplier.assessed_domains) > 0:
            return True
        return False

    def has_chosen_brief_category(self):
        if self.supplier and self.brief_domain and self.brief_domain.name in self.supplier.unassessed_domains:
            return True
        return False

    def has_evidence_in_draft_for_category(self):
        if self.supplier and self.brief_category:
            evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
                int(self.brief_category),
                self.supplier_code
            )
            if evidence and evidence.status == 'draft':
                return True
        return False

    def has_latest_evidence_rejected_for_category(self):
        if self.supplier and self.brief_category:
            evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
                int(self.brief_category),
                self.supplier_code
            )
            if evidence and evidence.status == 'rejected':
                return True
        return False

    def evidence_id_in_draft(self):
        if self.has_evidence_in_draft_for_category():
            evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
                int(self.brief_category),
                self.supplier_code
            )
            return evidence.id
        return None

    def evidence_id_rejected(self):
        if self.has_latest_evidence_rejected_for_category():
            evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
                int(self.brief_category),
                self.supplier_code
            )
            if evidence and evidence.status == 'rejected':
                return evidence.id
        return None

    def is_assessed_for_category(self):
        if self.supplier and self.brief_domain and self.brief_domain.name in self.supplier.assessed_domains:
            return True
        return False

    def is_awaiting_domain_assessment(self):
        if self.supplier and self.brief_category:
            evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
                int(self.brief_category),
                self.supplier_code
            )
            if evidence and evidence.status == 'submitted':
                return True

        if (
            self.supplier and self.brief_category and self.brief.data.get('openTo', '') == 'all' and
            assessments.get_open_assessments(
                domain_id=int(self.brief_category),
                supplier_code=self.supplier_code
            )
        ):
            return True

        return False

    def is_awaiting_application_assessment(self):
        if (
            self.supplier_code and
            application_service.get_submitted_application_ids(supplier_code=self.supplier_code)
        ):
            return True

        if self.user_role == 'applicant':
            application = application_service.find(id=self.current_user.application_id).one_or_none()
            if application and application.status == 'submitted' and application.type == 'new':
                return True

        return False

    def is_invited(self):
        if (
            self.user_role == 'supplier' and (
                self.brief.data.get('openTo', '') == 'all' or
                self.brief.data.get('sellerSelector', '') == 'allSellers' or
                str(self.supplier_code) in self.invited_sellers.keys() or (
                    self.brief.data.get('openTo', '') == 'category' and (
                        self.is_assessed_for_category()
                    )
                ) or (
                    self.brief.data.get('sellerSelector', '') == 'someSellers' and
                    self.current_user.email_address in self.brief.data.get('sellerEmailList', [])
                ) or (
                    self.brief.data.get('sellerSelector', '') == 'oneSeller' and
                    self.brief.data.get('sellerEmail', '') == self.current_user.email_address
                )
            )
        ):
            return True
        return False

    def has_been_assessed_for_brief(self):
        if self.supplier and evidence_service.supplier_has_assessment_for_brief(
            self.supplier_code,
            self.brief.id
        ):
            return True
        if self.supplier and assessments.supplier_has_assessment_for_brief(self.supplier_code, self.brief.id):
            return True
        return False

    def has_candidate_information(self):
        supplier_validator = SupplierValidator(self.supplier)
        errors = supplier_validator.validate_candidates()

        if len(errors) > 0:
            return False

        return True

    def can_respond_to_atm_opportunity(self):
        open_to = self.brief.data.get('openTo', '')

        if (
            self.user_role == 'supplier' and
            self.brief.lot.slug == 'atm' and
            self.supplier.data.get('recruiter', '') != 'yes' and (
                (open_to == 'all' and self.is_assessed_in_any_category()) or
                (open_to == 'category' and self.is_assessed_for_category())
            )
        ):
            return True

        return False

    def can_respond_to_rfx_or_training_opportunity(self):
        if (
            self.user_role == 'supplier' and (
                self.brief.lot.slug == 'rfx' or
                self.brief.lot.slug == 'training2'
            ) and
            self.supplier.data.get('recruiter', '') != 'yes' and
            str(self.supplier_code) in self.invited_sellers.keys() and
            self.is_assessed_for_category()
        ):
            return True

        return False

    def can_respond_to_specialist_opportunity(self):
        open_to = self.brief.data.get('openTo', '')

        if (
            self.user_role == 'supplier' and
            self.brief.lot.slug == 'specialist' and
            self.supplier.data.get('recruiter', '') in ['yes', 'both'] and (
                open_to == 'all' or (
                    open_to == 'selected' and
                    str(self.supplier_code) in self.invited_sellers.keys()
                )
            ) and self.has_candidate_information()
        ):
            return True

        return False

    def can_respond(self):
        if (
            self.can_respond_to_atm_opportunity() or
            self.can_respond_to_rfx_or_training_opportunity() or
            self.can_respond_to_specialist_opportunity()
        ):
            return True

        return False

    def has_responded(self, submitted_only=True):
        if self.user_role == 'supplier':
            responses = brief_responses_service.get_brief_responses(
                self.brief.id, self.supplier_code, submitted_only=submitted_only
            )
            brief_response_count = len(responses)
            lot = lots_service.find(
                slug='specialist'
            ).one_or_none()
            if self.brief.lot_id == lot.id:
                return brief_response_count >= int(self.brief.data.get('numberOfSuppliers', 0))
            elif brief_response_count > 0:
                return True
        return False

    def has_supplier_errors(self):
        if self.user_role != 'supplier':
            return False
        supplier_validator = SupplierValidator(self.supplier)
        messages = supplier_validator.validate_all()
        if len(messages.errors) > 0:
            return True
        return False

    def has_signed_current_agreement(self):
        if self.user_role != 'supplier':
            return True

        return has_signed_current_agreement(self.supplier)

    def is_consultant(self):
        if self.supplier and self.supplier.data.get('recruiter', '') == 'no':
            return True

        return False
