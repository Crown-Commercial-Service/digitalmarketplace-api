from app.api.helpers import Service
from app.models import BriefClarificationQuestion, User, db


class BriefClarificationQuestionService(Service):
    __model__ = BriefClarificationQuestion

    def __init__(self, *args, **kwargs):
        super(BriefClarificationQuestionService, self).__init__(*args, **kwargs)

    def get_answers(self, brief_id):
        result = (
            db
            .session
            .query(
                BriefClarificationQuestion.id,
                BriefClarificationQuestion._brief_id,
                BriefClarificationQuestion.published_at,
                BriefClarificationQuestion.question,
                BriefClarificationQuestion.answer,
                BriefClarificationQuestion.user_id,
                User.name
            )
            .join(User)
            .filter(BriefClarificationQuestion._brief_id == brief_id)
            .order_by(BriefClarificationQuestion.published_at)
            .all()
        )
        return [r._asdict() for r in result]
