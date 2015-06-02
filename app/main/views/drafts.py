from flask import jsonify, abort, request, current_app

from .. import main
from ...validation import is_valid_service_id_or_400
from ...models import Service


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

    return "things"


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

    return "things"
