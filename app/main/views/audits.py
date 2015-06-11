from flask import jsonify, abort, request, current_app
from ...models import AuditEvent
from sqlalchemy import asc
from ...utils import pagination_links
from .. import main
from dmutils.audit import AuditTypes


@main.route('/audit-events', methods=['GET'])
def list_audits():

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    audits = AuditEvent.query.order_by(
        asc(AuditEvent.created_at)
    )

    if request.args.get('audit-type'):
        if AuditTypes.is_valid_audit_type(request.args.get('audit-type')):
            audits = audits.filter(AuditEvent.type == request.args.get('audit-type'))
        else:
            abort(400, "Invalid audit type")

    audits = audits.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
    )

    return jsonify(
        auditEvents=[audit.serialize() for audit in audits.items],
        links=pagination_links(
            audits,
            '.list_audits',
            request.args
        )
    )