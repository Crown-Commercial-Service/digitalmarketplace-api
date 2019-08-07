from app.api.helpers import Service
from app.models import BriefQuestion, Supplier, db


class BriefQuestionService(Service):
    __model__ = BriefQuestion

    def __init__(self, *args, **kwargs):
        super(BriefQuestionService, self).__init__(*args, **kwargs)

    def get_questions(self, brief_id):
        result = (
            db
            .session
            .query(
                BriefQuestion.id,
                BriefQuestion.brief_id,
                BriefQuestion.created_at,
                BriefQuestion.data['question'].astext.label('question'),
                BriefQuestion.supplier_code,
                BriefQuestion.answered,
                Supplier.name.label('supplierName')
            )
            .join(Supplier)
            .filter(BriefQuestion.brief_id == brief_id)
            .order_by(BriefQuestion.created_at)
            .all()
        )
        return [r._asdict() for r in result]
