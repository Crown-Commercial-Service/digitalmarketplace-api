from flask import jsonify, abort, request, current_app
from ...models import AuditEvent
from sqlalchemy import asc
from ...utils import pagination_links
from .. import main


@main.route('/audits', methods=['GET'])
def list_audits():

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    audits = AuditEvent.query.filter.order_by(
        asc(AuditEvent.created_at)
    )

    audits = audits.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
    )

    return jsonify(
        services=[audits.serialize() for audits in audits.items],
        links=pagination_links(
            audits,
            '.list_audits',
            request.args
        )
    )