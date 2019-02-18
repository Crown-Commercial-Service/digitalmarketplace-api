from app.api.services import application_service, assessments, domain_service, suppliers, brief_responses_service


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

    def is_assessed_for_category(self):
        if self.supplier and self.brief_domain and self.brief_domain.name in self.supplier.assessed_domains:
            return True
        return False

    def is_awaiting_domain_assessment(self):
        if self.supplier and self.brief_category and assessments.get_open_assessments(
            domain_id=int(self.brief_category),
            supplier_code=self.supplier_code
        ):
            return True

        if self.supplier and self.brief.data.get('openTo', '') == 'all' and assessments.get_open_assessments(
            supplier_code=self.supplier_code
        ):
            return True

        return False

    def is_awaiting_application_assessment(self):
        if application_service.get_submitted_application_ids(supplier_code=self.supplier_code):
            return True

        if self.user_role == 'applicant':
            application = application_service.find(id=self.current_user.application_id).one_or_none()
            if application and application.status == 'submitted' and application.type == 'new':
                return True

        return False

    def has_been_assessed_for_brief(self):
        if self.supplier and assessments.supplier_has_assessment_for_brief(self.supplier_code, self.brief.id):
            return True
        return False

    def can_respond(self):
        if (self.user_role == 'supplier' and
            ((self.brief.data.get('openTo', '') == 'all' and self.is_assessed_in_any_category()) or
             (self.brief.data.get('openTo', '') == 'category' and self.is_assessed_for_category()) or
             str(self.supplier_code) in self.invited_sellers.keys())):
            return True
        return False

    def has_responded(self):
        if (self.user_role == 'supplier' and
            brief_responses_service.find(
                supplier_code=self.supplier_code,
                brief_id=self.brief.id,
                withdrawn_at=None).count() > 0):
            return True
        return False
