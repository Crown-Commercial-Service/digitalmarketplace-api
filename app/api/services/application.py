from app.api.helpers import Service
from app import db
from app.models import Application, BriefResponse
from sqlalchemy import and_, or_


class ApplicationService(Service):
    __model__ = Application

    def __init__(self, *args, **kwargs):
        super(ApplicationService, self).__init__(*args, **kwargs)

    def get_unassessed_applications(self, from_date=None):
        # The ultimate goal of this query is to get applications which are not assessed.
        # As a start we take all applications with a status of submitted.
        new_and_edit_criteria = and_(Application.status == 'submitted')

        # We also want to get applications where the supplier is active,
        # Active is defined by:
        #   Registered (application created date).
        #   Profile edit (application edit).
        #   AND applied for work (brief response).
        brief_response_query = (
            db.session
            .query(BriefResponse.supplier_code)
        )
        # Apply a date filter on the results.
        if from_date:
            new_and_edit_criteria = and_(Application.status == 'submitted',
                                         Application.created_at >= from_date)

            brief_response_query = brief_response_query.filter(BriefResponse.created_at >= from_date)

        # This is the applied for work criteria which returns applications
        # where a supplier has made a brief response
        applied_for_work_criteria = and_(
            Application.supplier_code.in_(brief_response_query),
            Application.type == 'edit',
            Application.status == 'submitted'
        )

        query = (
            db.session
            .query(
                Application.id,
                Application.data,
                Application.status,
                Application.created_at,
                Application.type
            )
            .filter(
                or_(
                    # Combining both the normal application query and whether a supplier has
                    # applied for work, we get a unique list of unassessed applications
                    new_and_edit_criteria,
                    applied_for_work_criteria
                )
            )
        )
        result = query.all()

        return [a._asdict() for a in result]
