import mock
import pytest
from app.encryption import checkpw, hashpw, authenticate_user


@pytest.mark.parametrize('user_is_locked, expected_auth_result', [(True, False), (False, True)])
def test_authenticate_user(user_is_locked, expected_auth_result):
    password = "mypassword"
    password_hash = hashpw(password)
    mock_user = mock.Mock(password=password_hash, locked=user_is_locked)

    assert authenticate_user(password, mock_user) == expected_auth_result


def test_should_hash_password():
    password = "mypassword"
    assert password != hashpw(password)


def test_should_check_password():
    password = "mypassword"
    password_hash = hashpw(password)
    assert checkpw(password, password_hash) is True


def test_should_check_invalid_password():
    password = "mypassword"
    password_hash = hashpw(password)
    assert checkpw("not my password", password_hash) is False
