from sqlalchemy import func
from app.api.helpers import Service
from app.models import Application, db


class ApplicationService(Service):
    __model__ = Application

    def __init__(self, *args, **kwargs):
        super(ApplicationService, self).__init__(*args, **kwargs)

    def get_submitted_application_ids(self, supplier_code=None):
        query = (db.session.query(Application.id)
                   .filter(Application.status == 'submitted'))

        if supplier_code:
            query = query.filter(Application.supplier_code == supplier_code)

        results = query.order_by(Application.id).all()

        return [r for (r, ) in results]

    def get_applications_by_abn(self, abn):
        return (
            db
            .session
            .query(
                Application
            )
            .filter(func.replace(Application.data['abn'].astext.label('abn'), ' ', '') == abn)
            .filter(Application.status != 'deleted')
            .all()
        )
