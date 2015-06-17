from datetime import datetime

from nose.tools import assert_equal, assert_raises
from sqlalchemy.exc import DataError

from app import db, create_app
from app.models import User, Framework


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


def test_framework_should_not_accept_invalid_status():
    app = create_app('test')
    with app.app_context(), assert_raises(DataError):
        f = Framework(
            name='foo',
            framework='gcloud',
            status='invalid',
            expired=False,
        )
        db.session.add(f)
        db.session.commit()


def test_framework_should_accept_valid_statuses():
    app = create_app('test')
    with app.app_context():
        for i, status in enumerate(Framework.STATUSES):
            f = Framework(
                name='foo',
                framework='gcloud',
                status=status,
                expired=False,
            )
            db.session.add(f)
            db.session.commit()
