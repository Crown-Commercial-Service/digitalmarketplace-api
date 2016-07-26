from flask import render_template, current_app, request, Response

from blueprint import admin

import streql  # Constant-time string comparison


@admin.before_request
def basic_auth():
    auth = request.authorization
    username = current_app.config['DM_API_ADMIN_USERNAME']
    password = current_app.config['DM_API_ADMIN_PASSWORD']
    if auth and auth.type == 'basic' and \
            streql.equals(auth.username, username) and streql.equals(auth.password, password):
        return
    return Response(status=401, headers={'WWW-Authenticate': 'Basic realm="DMP Admin"'})


@admin.route('/_admin', methods=['GET'])
def admin_index():
    return render_template('index.html')
