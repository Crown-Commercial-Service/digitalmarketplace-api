from datetime import datetime
from flask import render_template, session , redirect, url_for
from . import main

@main.route('/')
def index():
	return render_template('main.html')