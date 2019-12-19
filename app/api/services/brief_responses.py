from sqlalchemy import desc, func

from app import db
from app.api.helpers import Service
from app.models import BriefResponse, Supplier


class BriefResponsesService(Service):
    __model__ = BriefResponse

    def __init__(self, *args, **kwargs):
        super(BriefResponsesService, self).__init__(*args, **kwargs)

    def get_brief_responses(self, brief_id, supplier_code, order_by_status=False, submitted_only=False,
                            include_withdrawn=False):
        query = (
            db.session.query(BriefResponse.created_at,
                             BriefResponse.submitted_at,
                             BriefResponse.id,
                             BriefResponse.brief_id,
                             BriefResponse.supplier_code,
                             BriefResponse.status,
                             BriefResponse.data['respondToEmailAddress'].label('respondToEmailAddress'),
                             BriefResponse.data['specialistGivenNames'].label('specialistGivenNames'),
                             BriefResponse.data['specialistSurname'].label('specialistSurname'),
                             Supplier.name.label('supplier_name'))
            .join(Supplier)
            .filter(
                BriefResponse.brief_id == brief_id,
                BriefResponse.withdrawn_at.is_(None)
            )
        )
        if supplier_code:
            query = query.filter(BriefResponse.supplier_code == supplier_code)
        if submitted_only:
            query = query.filter(BriefResponse.submitted_at.isnot(None))
        if include_withdrawn:
            query = query.filter(BriefResponse.withdrawn_at.isnot(None))
        else:
            query = query.filter(BriefResponse.withdrawn_at.is_(None))
        if order_by_status:
            query = query.order_by(BriefResponse.status.asc(), BriefResponse.id.asc())
        else:
            query = query.order_by(BriefResponse.id.asc())

        return [r._asdict() for r in query.all()]

    def get_responses_to_zip(self, brief_id, slug):
        query = (
            db.session.query(BriefResponse)
                      .join(Supplier)
                      .filter(BriefResponse.brief_id == brief_id,
                              BriefResponse.withdrawn_at.is_(None),
                              BriefResponse.submitted_at.isnot(None))
                      .order_by(func.lower(Supplier.name))
        )

        if slug == 'digital-professionals':
            query = query.order_by(func.lower(BriefResponse.data['specialistName'].astext))
        elif slug == 'specialist':
            query = query.order_by(func.lower(BriefResponse.data['specialistGivenNames'].astext))

        return query.all()

    def get_suppliers_responded(self, brief_id):
        query = (
            db.session.query(
                BriefResponse.supplier_code,
                Supplier.name.label('supplier_name'))
            .distinct(BriefResponse.supplier_code, Supplier.name.label('supplier_name'))
            .join(Supplier)
            .filter(
                BriefResponse.brief_id == brief_id,
                BriefResponse.withdrawn_at.is_(None),
                BriefResponse.submitted_at.isnot(None)
            )
        )

        return [r._asdict() for r in query.all()]

    def get_all_attachments(self, brief_id):
        query = (
            db.session.query(BriefResponse.data['attachedDocumentURL'].label('attachments'),
                             BriefResponse.data['responseTemplate'].label('requirements'),
                             BriefResponse.data['writtenProposal'].label('proposal'),
                             BriefResponse.data['resume'].label('resume'),
                             BriefResponse.supplier_code,
                             Supplier.name.label('supplier_name'))
            .join(Supplier)
            .filter(
                BriefResponse.brief_id == brief_id,
                BriefResponse.withdrawn_at.is_(None),
                BriefResponse.submitted_at.isnot(None)
            )
        )
        responses = [r._asdict() for r in query.all()]
        attachments = []
        for response in responses:
            if 'attachments' in response and response['attachments']:
                for attachment in response['attachments']:
                    attachments.append({
                        'supplier_code': response['supplier_code'],
                        'supplier_name': response['supplier_name'],
                        'file_name': attachment
                    })
            if 'requirements' in response and response['requirements']:
                for requirement in response['requirements']:
                    attachments.append({
                        'supplier_code': response['supplier_code'],
                        'supplier_name': response['supplier_name'],
                        'file_name': requirement
                    })
            if 'proposal' in response and response['proposal']:
                for p in response['proposal']:
                    attachments.append({
                        'supplier_code': response['supplier_code'],
                        'supplier_name': response['supplier_name'],
                        'file_name': p
                    })
            if 'resume' in response and response['resume']:
                for resume in response['resume']:
                    attachments.append({
                        'supplier_code': response['supplier_code'],
                        'supplier_name': response['supplier_name'],
                        'file_name': resume
                    })
        return attachments

    def get_metrics(self):
        brief_response_count = (
            db
            .session
            .query(
                func.count(BriefResponse.id)
            )
            .filter(
                BriefResponse.data.isnot(None),
                BriefResponse.withdrawn_at.is_(None),
                BriefResponse.submitted_at.isnot(None)
            )
            .scalar()
        )

        return {
            "brief_response_count": brief_response_count
        }
