import pendulum
from flask import current_app
from sqlalchemy import or_
from app import db
from app.api.services import (
    briefs,
    key_values_service
)
from app.emails.briefs import send_brief_closed_email
from app.models import Brief, Framework, Lot
from . import celery


@celery.task
def process_closed_briefs():
    # find briefs that were closed yesterday. this task is designed to run after midnight.
    closed_briefs = (
        db
        .session
        .query(Brief)
        .join(Framework)
        .filter(
            Brief.closed_at >= pendulum.yesterday(tz='Australia/Canberra'),
            Brief.closed_at < pendulum.today(tz='Australia/Canberra'),
            Brief.withdrawn_at.is_(None),
            Framework.slug == 'digital-marketplace'
        )
        .all()
    )

    for closed_brief in closed_briefs:
        send_brief_closed_email(closed_brief)


@celery.task
def create_responses_zip_for_closed_briefs():
    from app.tasks.s3 import create_responses_zip, CreateResponsesZipException
    closed_briefs = (
        db
        .session
        .query(Brief)
        .join(
            Framework,
            Lot
        )
        .filter(
            Brief.status == 'closed',
            Brief.responses_zip_filesize.is_(None), (
                or_(
                    Lot.slug == 'digital-professionals',
                    Lot.slug == 'training',
                    Lot.slug == 'rfx'
                )
            ),
            Framework.slug == 'digital-marketplace')
        .all()
    )

    for brief in closed_briefs:
        try:
            create_responses_zip(brief.id)
        except CreateResponsesZipException as e:
            current_app.logger.error(str(e))


@celery.task
def update_brief_metrics():
    key_values_service.upsert('brief_metrics', briefs.get_metrics())
