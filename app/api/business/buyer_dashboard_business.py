from app.api.services import (
    briefs
)


def get_briefs(user_id, status=None):
    return briefs.get_buyer_dashboard_briefs(user_id, status)


def get_brief_counts(user_id):
    return briefs.get_brief_counts(user_id)
