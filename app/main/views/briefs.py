from flask import jsonify, abort

from .. import main
from ... import db
from ...utils import get_json_from_request, json_has_required_keys
from ...service_utils import validate_and_return_lot
from ...models import User, Brief


@main.route('/briefs', methods=['POST'])
def create_a_brief():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefs'])
    json_payload = json_payload['briefs']

    json_has_required_keys(json_payload, ['frameworkSlug', 'lot', 'userId'])

    framework, lot = validate_and_return_lot(json_payload)

    user = User.query.get(json_payload.pop('userId'))

    if user is None:
        abort(400, "User ID does not exist")

    brief = Brief(data={}, users=[user], framework=framework, lot=lot)

    db.session.add(brief)
    db.session.commit()

    return jsonify(), 201


@main.route('/briefs/<int:brief_id>', methods=['GET'])
def get_brief(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    return jsonify(briefs=brief.serialize())
