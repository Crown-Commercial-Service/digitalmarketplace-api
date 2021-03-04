from app import db
from app.models import Application, AuditEvent, AuditTypes
from helpers import notify_team
from app.tasks import publish_tasks


def create_application(email_address=None, name=None, abn=None, organisation_name=None, postcode=None, state=None):
    application = Application(
        status='saved',
        data={
            'framework': 'digital-marketplace',
            'email': email_address,
            'abn': abn,
            'name': organisation_name,
            'addresses': {'0': {'address_line': "", 'postal_code': postcode, 'state': state}}
        }
    )

    db.session.add(application)
    db.session.flush()

    audit = AuditEvent(
        audit_type=AuditTypes.create_application,
        user='',
        data={},
        db_object=application
    )

    db.session.add(audit)
    db.session.commit()

    publish_tasks.application.delay(
        publish_tasks.compress_application(application),
        'created',
        name=name,
        email_address=email_address,
        from_expired=False
    )

    return application
