from flask import render_template

from blueprint import admin


@admin.route('/_admin', methods=['GET'])
def admin_index():
    return render_template('index.html')
