import rollbar
from flask import jsonify, request
from flask_login import current_user, login_required

from app.api import api
from app.api.business import team_business
from app.api.business.errors import NotFoundError, TeamError, ValidationError, UnauthorisedError
from app.api.helpers import (
    abort,
    forbidden,
    role_required,
    not_found,
    exception_logger
)
from app.api.services import team_member_service
from ...utils import get_json_from_request


@api.route('/teams', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_teams_overview():
    team = team_business.get_teams_overview()

    return jsonify(team)


@api.route('/people', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_people_overview():
    team = team_business.get_people_overview()

    return jsonify(team)


@api.route('/team/create', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
def create_team():
    try:
        team = team_business.create_team()
    except TeamError as e:
        abort(str(e))
    except NotFoundError as e:
        return not_found(str(e))
    except UnauthorisedError as e:
        return forbidden(str(e))

    return jsonify(team)


@api.route('/team/<int:team_id>', methods=["GET"])
@exception_logger
@login_required
@role_required('buyer')
def get_team(team_id):
    team = None
    try:
        team = team_business.get_team(team_id)
    except NotFoundError as e:
        return not_found(str(e))
    except UnauthorisedError as e:
        return forbidden(str(e))

    return jsonify(team)


@api.route('/team/<int:team_id>/update', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
def update_team(team_id):
    data = get_json_from_request()
    try:
        team = team_business.update_team(team_id, data)
    except ValidationError as e:
        return abort(str(e))
    except NotFoundError as e:
        return not_found(str(e))
    except UnauthorisedError as e:
        return forbidden(str(e))

    return jsonify(team)


@api.route('/team/members/search', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def find_team_members():
    keywords = request.args.get('keywords') or ''
    exclude = request.args.get('exclude') or ''

    if keywords:
        results = team_business.search_team_members(
            current_user,
            current_user.agency_id,
            keywords=keywords,
            exclude=exclude.split(',')
        )

        return jsonify(users=results), 200
    else:
        abort('You must provide a keywords param.')


@api.route('/team/request-access', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
def request_access():
    data = get_json_from_request()

    try:
        team_business.request_access(data)
    except ValidationError as e:
        abort(str(e))

    return jsonify(success=True)


@api.route('/team/<int:team_id>/request-join', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
def request_to_join(team_id):
    try:
        team_business.request_to_join(current_user.email_address, team_id, current_user.agency_id)
    except NotFoundError as e:
        return not_found(str(e))
    except UnauthorisedError as e:
        return forbidden(str(e))
    except ValidationError as e:
        abort(str(e))

    return jsonify(success=True)


@api.route('/team/join-requests', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_join_requests():
    join_requests = team_business.get_join_requests(current_user.email_address)
    results = {}
    if join_requests:
        for request in join_requests:
            if request.data['team_id'] not in results:
                results[request.data['team_id']] = []
            results[request.data['team_id']].append({
                "id": request.id,
                "team_id": request.data['team_id'],
                "created_at": request.created_at
            })
    return jsonify(join_requests=results)


@api.route('/team/join-request/<int:team_id>/<string:token>', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
def get_join_request(team_id, token):
    try:
        team = team_business.get_team(team_id)
    except NotFoundError as e:
        return not_found(str(e))
    except UnauthorisedError as e:
        return forbidden(str(e))

    join_request = team_business.get_join_request(token)
    if not join_request or int(join_request.data['team_id']) != team_id:
        return not_found('The token is invalid, or this request has already been declined or accepted')

    return jsonify(join_request=join_request)


@api.route('/team/decline-join-request/<int:team_id>/<string:token>', methods=['POST'])
@exception_logger
@login_required
@role_required('buyer')
def decline_join_request(team_id, token):
    data = get_json_from_request()

    if 'reason' not in data or not data['reason']:
        abort('Must provide reason for decline')

    try:
        team = team_business.get_team(team_id)
    except NotFoundError as e:
        return not_found(str(e))
    except UnauthorisedError as e:
        return forbidden(str(e))

    join_request = team_business.get_join_request(token)
    if not join_request or int(join_request.data['team_id']) != team_id:
        return not_found('The token is invalid, or this request has already been declined or accepted')

    if (
        'user_id' in join_request.data and
        (
            team_member_service.get_team_members_by_user_id(team_id, [int(join_request.data['user_id'])]) or
            team_member_service.get_team_leads_by_user_id(team_id, [int(join_request.data['user_id'])])
        )
    ):
        abort('This user is already a member of the team')

    team_business.decline_join_request(join_request, data['reason'], team_id)

    return jsonify(success=True)
