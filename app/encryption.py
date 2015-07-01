from flask.ext.bcrypt import generate_password_hash, \
    check_password_hash


def authenticate_user(password, user):
    return not user.locked and checkpw(password, user.password)


def hashpw(password):
    return generate_password_hash(password, 10)


def checkpw(password, hashed_password):
    return check_password_hash(hashed_password, password)
