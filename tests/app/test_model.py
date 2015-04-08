from nose.tools\
    import assert_equal
from app.models import User
from datetime import datetime


def test_should_not_return_password_on_user():
    now = datetime.now()
    user = User(
        email_address='email',
        name='name',
        password='password',
        active=True,
        locked=False,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    assert_equal(user.serialize()['email'], "email")