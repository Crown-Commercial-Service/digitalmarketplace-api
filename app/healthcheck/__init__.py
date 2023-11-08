# Add an unauthenticated /healthcheck route for ECS Task & ALB Target
# Group health checks. Simply indicates that the app is "up".
from flask import Blueprint, jsonify

healthcheck = Blueprint('healthcheck', __name__, url_prefix='/healthcheck')


@healthcheck.route('/')
@healthcheck.route('')
def healthcheck_root():
    return jsonify(status='ok'), 200
