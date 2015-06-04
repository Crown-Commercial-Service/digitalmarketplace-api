from flask import jsonify, abort

from sqlalchemy.exc import IntegrityError

from .. import main
from ... import db
from ...validation import is_valid_service_id_or_400
from ...models import Service, DraftService, ArchivedService
from ...service_utils import validate_and_return_updater_request, \
    update_and_validate_service, validate_and_return_service_request, \
    index_service


@main.route('/services/<string:service_id>/draft', methods=['PUT'])
def create_draft_service(service_id):
    """
    Create a draft service from an existing service
    :param service_id:
    :return:
    """
    is_valid_service_id_or_400(service_id)
    updater_json = validate_and_return_updater_request()

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
        abort(400, "Database Error: {0}".format(e))


@main.route('/services/<string:service_id>/draft', methods=['POST'])
def edit_draft_service(service_id):
    """
    Edit a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    updater_json = validate_and_return_updater_request()
    update_json = validate_and_return_service_request(service_id)

    service = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    service.update_from_json(
        update_json,
        updated_by=updater_json['updated_by'],
        updated_reason=updater_json['update_reason'])

    db.session.add(service)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(services=service.serialize()), 200


@main.route('/services/<string:service_id>/draft', methods=['GET'])
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


@main.route('/services/<string:service_id>/draft', methods=['DELETE'])
def delete_draft_service(service_id):
    """
    Delete a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    updater_json = validate_and_return_updater_request()

    service = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    db.session.delete(service)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>/draft/publish', methods=['POST'])
def publish_draft_service(service_id):
    """
    Delete a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    updater_json = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    service = Service.query.filter(
        Service.service_id == draft.service_id
    ).first_or_404()

    archived_service = ArchivedService.from_service(service)
    new_service = update_and_validate_service(
        service,
        draft.data,
        updater_json)

    db.session.add(archived_service)
    db.session.add(new_service)
    db.session.delete(draft)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    index_service(new_service)

    return jsonify(services=new_service.serialize()), 200
