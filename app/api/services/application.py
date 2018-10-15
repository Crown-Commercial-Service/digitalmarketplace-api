from app.api.helpers import Service
from app.models import Application, db


class ApplicationService(Service):
    __model__ = Application

    def __init__(self, *args, **kwargs):
        super(ApplicationService, self).__init__(*args, **kwargs)

    def get_submitted_application_ids(self):
        results = (db.session.query(Application.id)
                   .filter(Application.status == 'submitted')
                   .order_by(Application.id)
                   .all())

        return [r for (r, ) in results]
