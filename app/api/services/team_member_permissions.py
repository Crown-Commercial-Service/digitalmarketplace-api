from app.api.helpers import Service
from app.models import TeamMemberPermission


class TeamMemberPermissionService(Service):
    __model__ = TeamMemberPermission

    def __init__(self, *args, **kwargs):
        super(TeamMemberPermissionService, self).__init__(*args, **kwargs)
