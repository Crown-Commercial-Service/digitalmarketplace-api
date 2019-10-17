from flask_bcrypt import generate_password_hash, check_password_hash


def authenticate_user(password, user):
    return checkpw(password, user.password) and not user.locked


def hashpw(password):
    return generate_password_hash(password, 10).decode('utf-8')


def checkpw(password, hashed_password):
    return check_password_hash(hashed_password, password)
