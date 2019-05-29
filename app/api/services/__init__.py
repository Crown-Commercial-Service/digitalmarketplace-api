from .agency import AgencyService
from .application import ApplicationService
from .audit import AuditService, AuditTypes
from .assessments import AssessmentsService
from .domain import DomainService
from .briefs import BriefsService
from .suppliers import SuppliersService
from .supplier_domain import SupplierDomainService
from .lots import LotsService
from .brief_overview import BriefOverviewService
from .brief_responses import BriefResponsesService
from .users import UsersService
from .key_value import KeyValueService
from .publish import Publish
from .frameworks import FrameworksService
from .user_claims import UserClaimService

agency_service = AgencyService()
application_service = ApplicationService()
audit_service = AuditService()
audit_types = AuditTypes
assessments = AssessmentsService()
domain_service = DomainService()
briefs = BriefsService()
suppliers = SuppliersService()
supplier_domain_service = SupplierDomainService()
lots_service = LotsService()
brief_overview_service = BriefOverviewService()
brief_responses_service = BriefResponsesService()
users = UsersService()
key_values_service = KeyValueService()
publish = Publish()
frameworks_service = FrameworksService()
user_claims_service = UserClaimService()
