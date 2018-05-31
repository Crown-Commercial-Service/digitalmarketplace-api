import json
from app.models import db, User, BriefAssessor


def test_get_assessors(bearer, client, briefs):
    email_address = 'test@digital.gov.au'
    client.post('/2/login', data=json.dumps({
        'emailAddress': email_address, 'password': 'testpassword'
    }), content_type='application/json')

    user = User.query.filter(User.email_address == email_address).first()
    brief = briefs[0]

    db.session.add(BriefAssessor(
        brief_id=brief.id,
        user_id=user.id
    ))

    db.session.add(BriefAssessor(
        brief_id=brief.id,
        email_address='assessor@digital.gov.au'
    ))

    db.session.commit()

    res = client.get('/2/brief/{}/assessors'.format(brief.id))
    assert res.status_code == 200
    data = json.loads(res.get_data(as_text=True))
    assert data[0]['brief_id'] == brief.id
    assert data[0]['user_email_address'] == email_address
    assert data[1]['email_address'] == 'assessor@digital.gov.au'
