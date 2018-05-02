import json
import pytest
import pendulum

from app.models import (db,
                        Application)
from faker import Faker

fake = Faker()


@pytest.fixture()
def unassessed_applications(app, request):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Application(
                id=(i),
                data={
                    "name": "Test Application",
                    "services": {
                        "Data science": True
                    },
                    "case_studies": {
                        "0": {
                            "id": 0,
                            "service": "Data science"
                        }
                    }
                },
                created_at=pendulum.utcnow(),
                status="submitted",
                type="edit"
            ))

        db.session.add(Application(
            id=7,
            data={
                "name": "Test Application",
                "services": {
                    "Data science": True
                },
                "case_studies": {
                    "0": {
                        "id": 0,
                        "service": "Data science"
                    }
                }
            },
            created_at=pendulum.parse('2017-01-01'),
            status="submitted",
            type="edit"
        ))

        db.session.add(Application(
            id=8,
            data={
                "name": "Test Application",
                "services": {
                    "Data science": True
                },
                "case_studies": {
                    "0": {
                        "id": 0,
                        "service": "Data science"
                    }
                }
            },
            created_at=pendulum.parse('2018-01-01'),
            status="saved",
            type="edit"
        ))

        db.session.add(Application(
            id=9,
            data={
                "name": "Test Application",
                "services": {
                    "Data science": True
                },
                "case_studies": {
                    "0": {
                        "id": 0,
                        "service": "Data science"
                    }
                }
            },
            created_at=pendulum.parse('2018-01-01'),
            status="submitted",
            type="new"
        ))
        db.session.flush()

        db.session.commit()
        yield Application.query.all()


def test_can_list_with_date_filter(client, admin_users, unassessed_applications, services, domains):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'testadmin@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/application/unaccessed?from_date=2018-01-01')
    data = json.loads(response.get_data())

    assert response.status_code == 200
    assert len(data) == 6


def test_can_list(client, admin_users, unassessed_applications, services, domains):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'testadmin@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/application/unaccessed')
    data = json.loads(response.get_data())

    assert response.status_code == 200
    assert len(data) == 7
