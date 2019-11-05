from .agencies import AgenciesService
from .briefs import BriefsService
from .brief_responses import BriefResponsesService
from .suppliers import SuppliersService
# This is for report only queries.
# The queries here should not be used by normal application code.
# Since the queries for this will generally by quiet complex,
# you will find text based queries here.
agencies_service = AgenciesService()
briefs_service = BriefsService()
brief_responses_service = BriefResponsesService()
suppliers_service = SuppliersService()
