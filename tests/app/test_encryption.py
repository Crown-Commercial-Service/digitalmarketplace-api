from nose.tools import assert_equal, assert_not_equal

from app.encryption import checkpw, hashpw


def test_should_hash_password():
    password = "mypassword"
    assert_not_equal(password, hashpw(password))


def test_should_check_password():
    password = "mypassword"
    password_hash = hashpw(password)
    assert_equal(checkpw(password, password_hash), True)


def test_should_check_invalid_password():
    password = "mypassword"
    password_hash = hashpw(password)
    assert_equal(checkpw("not my password", password_hash), False)
