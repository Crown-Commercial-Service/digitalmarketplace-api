import pendulum
from app.api.services import insight_service
from app.api.business.errors import NotFoundError


def get_insight(current_user, now):
    role = current_user.role if hasattr(current_user, 'role') else None
    if role == 'admin':
        insight = insight_service.get_insight(now, False)
    else:
        insight = insight_service.get_insight(now)

    if not insight:
        raise NotFoundError("Invalid date '{}'".format(now))

    return insight.get('data')


def upsert(now, data=None, active=None):
    existing = insight_service.get_insight_for_update(now)
    saved = None
    if existing:
        if data is not None:
            existing.data = data
        if active is not None:
            existing.active = active
        saved = insight_service.save(existing)
    else:
        saved = insight_service.create(
            data=data,
            active=active if active else False,
            published_at=now.start_of('month')
        )

    return {
        "data": saved.data,
        "published_at": saved.published_at,
        "active": saved.active
    } if saved else None
