from dmutils.audit import AuditTypes
from nose.tools import assert_equal, assert_raises
from app.models import User, AuditEvent
from datetime import datetime


def test_should_not_return_password_on_user():
    now = datetime.now()
    user = User(
        email_address='email',
        name='name',
        role='buyer',
        password='password',
        active=True,
        locked=False,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    assert_equal(user.serialize()['emailAddress'], "email")
    assert_equal(user.serialize()['name'], "name")
    assert_equal(user.serialize()['role'], "buyer")
    assert_equal('password' in user.serialize(), False)
