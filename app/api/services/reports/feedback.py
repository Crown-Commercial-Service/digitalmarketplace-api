from app.api.helpers import Service
from app.models import AuditEvent
from app import db
from sqlalchemy import func


class FeedbackService(Service):
    __model__ = AuditEvent

    def __init__(self, *args, **kwargs):
        super(FeedbackService, self).__init__(*args, **kwargs)

    def get_all_feedback(self):
        result = (
            db
            .session
            .query(
                AuditEvent.created_at,
                AuditEvent.user,
                AuditEvent.data['objectAction'].astext.label('action'),
                AuditEvent.data['difficultyQuestion'].astext.label('difficultyQuestion'),
                AuditEvent.data['difficulty'].astext.label('difficulty'),
                AuditEvent.data['allowFurtherFeedback'].astext.label('allowFurtherFeedback'),
                AuditEvent.data['contact_for_user_research'].astext.label('contactForUserResearch'),
                AuditEvent.data['commentQuestion'].astext.label('commentQuestion'),
                AuditEvent.data['comment'].astext.label('comment'),
            )
            .filter(AuditEvent.type == 'feedback')
            .order_by(AuditEvent.id)
            .all()
        )
        return [r._asdict() for r in result]
