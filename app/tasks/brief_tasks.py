from . import celery
from app import db
from app.models import Brief, Framework
from app.emails.briefs import send_brief_closed_email
import pendulum


@celery.task
def process_closed_briefs():
    # find briefs that were closed yesterday. this task is designed to run after midnight.
    closed_briefs = (db.session.query(Brief).join(Framework)
                                            .filter(Brief.closed_at >= pendulum.yesterday(tz='Australia/Canberra'),
                                                    Brief.closed_at < pendulum.today(tz='Australia/Canberra'),
                                                    Brief.withdrawn_at.is_(None),
                                                    Framework.slug == 'digital-marketplace')
                                            .all())

    for closed_brief in closed_briefs:
        send_brief_closed_email(closed_brief)
