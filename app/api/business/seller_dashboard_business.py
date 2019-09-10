from app.api.services import (
    seller_dashboard_service
)


def get_team_members(user_id):
    return seller_dashboard_service.get_team_members(user_id)
