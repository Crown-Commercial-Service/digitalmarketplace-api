# -*- coding: utf-8 -*-

from app.emails import render_email_template, escape_token_markdown

EXPECTED = """<!DOCTYPE html>
<html>
<head lang="en">
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet">
</head>
<body style="font-family: Open Sans, sans-serif; font-size: 17px;">
<div style="padding: 0rem; border: 2px solid #007554; font-size: 2rem;"><p style="background: white; margin: 0;">
<span style="background: #007554; padding: 1rem; display: inline-block;
line-height: 2rem; width: 3rem; margin-right: 1rem;">
<span style="text-align: center; width: 2rem; background: white; padding: 0.5rem; display: inline-block;
color: #007554; border-radius: 2rem;">&#x2714;</span>
</span>We've received your application.</div>
<div>
<h1 style="font-weight: bold;">Sample email</h1>
<p>Must handle ünicode &amp; ascii in the template.</p>
<p>And from a variable ünicode &amp; ascii &lt;marquee&gt;no marquee&lt;/marquee&gt;
&lt;blink script=&#34;window.alert(&#39;xss issue&#39;);&#34;&gt;no blink&lt;/blink&gt;.</p>
</div>
</body>
</html>"""


def test_render_email_template():
    rendered = render_email_template(
        'example.md',
        variable='ünicode & ascii <marquee>no marquee</marquee>\n'
                 '<blink script="window.alert(\'xss issue\');">no blink</blink>',
        styles={'h1': 'font-weight: bold'},
        header='<div style="padding: 0rem; border: 2px solid #007554; font-size: 2rem;">'
               '<p style="background: white; margin: 0;">\n<span style="background: #007554; padding: 1rem; '
               'display: inline-block;\nline-height: 2rem; width: 3rem; margin-right: 1rem;">\n'
               '<span style="text-align: center; width: 2rem; background: white; padding: 0.5rem; '
               'display: inline-block;\ncolor: #007554; border-radius: 2rem;">&#x2714;</span>\n'
               '</span>We\'ve received your application.</div>'
    )
    assert rendered == EXPECTED


def test_escape_token_markdown():
    token = 'randomtoken-_withmarkdown_-inthemiddle'
    expected = 'randomtoken\-\_withmarkdown\_\-inthemiddle'

    assert escape_token_markdown(token) == expected
