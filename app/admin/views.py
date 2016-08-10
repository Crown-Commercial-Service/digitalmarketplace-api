from flask import current_app, jsonify, render_template, request, Response
import streql  # Constant-time string comparison
from elasticsearch import TransportError

from app.search_indices import delete_indices, create_indices
from app.admin.blueprint import admin


@admin.before_request
def basic_auth():
    auth = request.authorization
    username = current_app.config['DM_API_ADMIN_USERNAME']
    password = current_app.config['DM_API_ADMIN_PASSWORD']
    if username is None:
        return
    if auth and auth.type == 'basic' and \
            streql.equals(auth.username, username) and streql.equals(auth.password, password):
        return
    return Response(status=401, headers={'WWW-Authenticate': 'Basic realm="DMP Admin"'})


@admin.route('/_admin', methods=['GET'])
def admin_index():
    return render_template('index.html')


@admin.route('/_admin/rebuild-index', methods=['POST'])
def rebuild_index():
    try:
        delete_indices()
    except TransportError, e:
        if e.status_code != 404:
            raise
    create_indices()
    return jsonify(message="done"), 200
