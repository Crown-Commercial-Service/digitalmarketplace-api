from flask import jsonify, abort, request, current_app

from sqlalchemy.exc import IntegrityError

from .. import main
from ... import db
from ...validation import is_valid_service_id_or_400
from ...models import Service, DraftService


@main.route('/services/<string:service_id>/draft',  methods=['PUT'])
def create_draft_service(service_id):
    """
    Create a draft service from an existing service
    :param service_id:
    :return:
    """
    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    draft = DraftService.from_service(service)

    db.session.add(draft)

    try:
        db.session.commit()
        return jsonify(services=draft.serialize()), 201
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig.message)


@main.route('/services/<string:service_id>/draft',  methods=['POST'])
def edit_draft_service(service_id):
    """
    Edit a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    return "things"


@main.route('/services/<string:service_id>/draft',  methods=['GET'])
def fetch_draft_service(service_id):
    """
    Return a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    service = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    return jsonify(services=service.serialize())


@main.route('/services/<string:service_id>/draft',  methods=['DELETE'])
def delete_draft_service(service_id):
    """
    Delete a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    service = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    db.session.delete(service)
    db.session.commit()

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>/draft/publish',  methods=['POST'])
def publish_draft_service(service_id):
    """
    Delete a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    service = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    return jsonify(services=service.serialize()), 401
