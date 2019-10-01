from app.api.services import (
    seller_dashboard_service
)


def get_team_members(supplier_code):
    return seller_dashboard_service.get_team_members(supplier_code)
