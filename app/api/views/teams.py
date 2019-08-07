import rollbar
from flask import jsonify, request
from flask_login import current_user, login_required

from app.api import api
from app.api.business import team_business
from app.api.business.errors import NotFoundError, TeamError, ValidationError, UnauthorisedError
from app.api.helpers import (
    abort,
    forbidden,
    get_email_domain,
    role_required,
    not_found,
    exception_logger
)
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
        abort(e.message)
    except NotFoundError as e:
        return not_found(e.message)
    except UnauthorisedError as e:
        return forbidden(e.message)
    except Exception as e:
        rollbar.report_exc_info()

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
        return not_found(e.message)
    except UnauthorisedError as e:
        return forbidden(e.message)

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
        return abort(e.message)
    except NotFoundError as e:
        return not_found(e.message)
    except UnauthorisedError as e:
        return forbidden(e.message)

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
            get_email_domain(current_user.email_address),
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
        abort(e.message)

    return jsonify(success=True)
