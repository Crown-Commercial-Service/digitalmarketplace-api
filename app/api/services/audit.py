from enum import Enum

import rollbar

from app.api.helpers import Service
from app.models import AuditEvent


class AuditService(Service):
    __model__ = AuditEvent

    def __init__(self, *args, **kwargs):
        super(AuditService, self).__init__(*args, **kwargs)

    def log_audit_event(self, **kwargs):
        try:
            audit = AuditEvent(
                audit_type=kwargs['audit_type'],
                user=kwargs['user'],
                data=kwargs['data'],
                db_object=kwargs['db_object']
            )
            self.save(audit)
        except Exception:
            rollbar.report_exc_info(extra_data={
                'audit_type': kwargs['audit_type'],
                'id': kwargs['db_object'].id
            })


class AuditTypes(Enum):
    update_price = 'update_price'
    sent_closed_brief_email = 'sent_closed_brief_email'
    update_brief_response = 'update_brief_response'
    update_brief_response_contact = 'update_brief_response_contact'
    update_application = 'update_application'
    update_application_admin = 'update_application_admin'
    create_application = 'create_application'
    submit_application = 'submit_application'
    revert_application = 'revert_application'
    approve_application = 'approve_application'
    reject_application = 'reject_application'
    delete_application = 'delete_application'
    create_brief = 'create_brief'
    update_brief_admin = 'update_brief_admin'
    update_brief = 'update_brief'
    update_brief_status = 'update_brief_status'
    create_brief_response = 'create_brief_response'
    read_brief_responses = 'read_brief_responses'
    add_brief_clarification_question = 'add_brief_clarification_question'
    delete_brief = 'delete_brief'
    seller_requested_feedback_from_buyer_email = 'seller_requested_feedback_from_buyer_email'
    seller_to_review_pricing_case_study_email = 'seller_to_review_pricing_case_study_email'
    seller_invited_to_rfx_opportunity = 'seller_invited_to_rfx_opportunity'
    seller_invited_to_training_opportunity = 'seller_invited_to_training_opportunity'
    seller_invited_to_atm_opportunity = 'seller_invited_to_atm_opportunity'
    seller_added_to_rfx_opportunity_admin = 'seller_added_to_rfx_opportunity_admin'
    seller_removed_from_rfx_opportunity_admin = 'seller_removed_from_rfx_opportunity_admin'
    seller_to_review_pricing_case_study_email_part_2 = 'seller_to_review_pricing_case_study_email_part_2'
    seller_to_review_pricing_case_study_email_part_3 = 'seller_to_review_pricing_case_study_email_part_3'
    sent_expiring_documents_email = 'sent_expiring_documents_email'
    create_team = 'create_team'
    specialist_brief_published = 'specialist_brief_published'
    specialist_brief_closed_email = 'specialist_brief_closed_email'
    seller_invited_to_specialist_opportunity = 'seller_invited_to_specialist_opportunity'
    specialist_brief_response_received_email = 'specialist_brief_response_received_email'
    update_supplier = 'update_supplier'
    notify_auth_rep_accept_master_agreement = 'notify_auth_rep_accept_master_agreement'
    declined_master_agreement = 'declined_master_agreement'
    accepted_master_agreement = 'accepted_master_agreement'
    declined_master_agreement_email = 'declined_master_agreement_email'
    create_work_order = 'create_work_order'
    create_brief_question = 'create_brief_question'
    create_brief_clarification_question = 'create_brief_clarification_question'
    team_lead_added = 'team_lead_added'
    team_member_added = 'team_member_added'
    team_member_removed = 'team_member_removed'
    sent_brief_question_to_buyer = 'sent_brief_question_to_buyer'
    sent_brief_question_to_seller = 'sent_brief_question_to_seller'
    sent_request_access = 'sent_request_access'
    evidence_draft_deleted = 'evidence_draft_deleted'
    agency_updated = 'agency_updated'
