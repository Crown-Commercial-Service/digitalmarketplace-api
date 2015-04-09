from flask import render_template

from . import explorer


@explorer.route('/_explorer')
def explorer():
    return render_template('explorer.html')
