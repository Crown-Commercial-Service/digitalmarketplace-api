from .agency import AgencyService
from .api_key import ApiKeyService
from .application import ApplicationService
from .assessments import AssessmentsService
from .audit import AuditService, AuditTypes
from .brief_clarification_question import BriefClarificationQuestionService
from .brief_question import BriefQuestionService
from .brief_response_download import BriefResponseDownloadService
from .brief_responses import BriefResponsesService
from .briefs import BriefsService
from .domain import DomainService
from .domain_criteria import DomainCriteriaService
from .evidence import EvidenceService
from .evidence_assessment import EvidenceAssessmentService
from .frameworks import FrameworksService
from .insight import InsightService
from .key_value import KeyValueService
from .lots import LotsService
from .master_agreement import MasterAgreementService
from .publish import Publish
from .seller_dashboard import SellerDashboardService
from .signed_agreement import SignedAgreementService
from .supplier_domain import SupplierDomainService
from .suppliers import SuppliersService
from .team_member_permissions import TeamMemberPermissionService
from .team_members import TeamMemberService
from .teams import TeamService
from .user_claims import UserClaimService
from .users import UsersService
from .work_order import WorkOrderService

agency_service = AgencyService()
signed_agreement_service = SignedAgreementService()
application_service = ApplicationService()
audit_service = AuditService()
audit_types = AuditTypes
assessments = AssessmentsService()
domain_service = DomainService()
domain_criteria_service = DomainCriteriaService()
briefs = BriefsService()
suppliers = SuppliersService()
supplier_domain_service = SupplierDomainService()
lots_service = LotsService()
brief_responses_service = BriefResponsesService()
users = UsersService()
key_values_service = KeyValueService()
publish = Publish()
frameworks_service = FrameworksService()
team_service = TeamService()
team_member_service = TeamMemberService()
team_member_permission_service = TeamMemberPermissionService()
user_claims_service = UserClaimService()
evidence_service = EvidenceService()
evidence_assessment_service = EvidenceAssessmentService()
work_order_service = WorkOrderService()
brief_question_service = BriefQuestionService()
brief_clarification_question_service = BriefClarificationQuestionService()
brief_response_download_service = BriefResponseDownloadService()
seller_dashboard_service = SellerDashboardService()
api_key_service = ApiKeyService()
insight_service = InsightService()
master_agreement_service = MasterAgreementService()
