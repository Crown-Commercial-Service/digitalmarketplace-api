# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from app.emails import render_email_template


EXPECTED = """<!DOCTYPE html>
<html>
<head lang="en">
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet">
</head>
<body style="font-family: Open Sans, sans-serif; font-size: 17px;">

<div>
<h1 style=" font-weight: bold">Sample email</h1>
<p>Must handle ünicode in the template.</p>
<p>And from a template ünicode.</p>
</div>
</body>
</html>"""


def test_render_email_template():
    rendered = render_email_template(
        'example.md',
        variable='ünicode',
        styles={'h1': 'font-weight: bold'})
    assert rendered == EXPECTED
