from flask import current_app, jsonify, request
from flask_login import login_required
from app.api import api
from app.api.services import application_service, users, domain_service
from app.api.helpers import role_required
from pendulum import Pendulum


@api.route('/application/unaccessed', methods=['GET'])
@login_required
@role_required('admin')
def get_unaccessed_applications():
    """Get Unassessed Applications
    ---
    tags:
      - "Application"
    security:
      - basicAuth: []
    parameters:
      - name: from_date
        in: query
        type: date
        required: false
    definitions:
      Application:
        type: object
        properties:
          id:
            type: number
          name:
            type: string
          areaOfExpertise:
            type: string
          caseStudyUrl:
            type: array
            items:
              type: string
          lastLogin:
            type: string
    responses:
      200:
        description: A list of unassessed domains
        schema:
          id: Application
    """
    from_date = request.args.get('from_date', None)
    if from_date:
        from_date = Pendulum.parse(from_date)
    applications = application_service.get_unassessed_applications(from_date)
    result = []
    frontend_address = current_app.config['FRONTEND_ADDRESS']
    domains = domain_service.all()
    for application in applications:
        services = application['data']['services']

        user = users.get_supplier_last_login(application['id'])
        if user:
            last_login = user.logged_in_at
        else:
            last_login = None

        for service in services.keys():
            domain = next((d for d in domains if d.name == service), None)
            case_studies = []
            for v in application['data'].get('case_studies').itervalues():
                if 'id' in v and v['service'] == service:
                    case_studies.append(v['id'])

            item = {
                "id": '{}-{}'.format(application['id'], domain.id),
                "name": application['data']['name'],
                "areaOfExpertise": service,
                "caseStudyUrl": ['{}/case-study/{}'.format(frontend_address, csi) for csi in case_studies],
                "lastLogin": last_login
            }
            if len(case_studies) > 0:
                result.append(item)

    return jsonify(result), 200
