from app.api.helpers import Service
from app.models import TeamBrief, db


class TeamBriefService(Service):
    __model__ = TeamBrief

    def __init__(self, *args, **kwargs):
        super(TeamBriefService, self).__init__(*args, **kwargs)
