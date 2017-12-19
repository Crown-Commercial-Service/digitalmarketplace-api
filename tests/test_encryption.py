from app.encryption import checkpw, hashpw


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
