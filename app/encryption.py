import bcrypt


def hashpw(password):
    return bcrypt.hashpw(password.encode('UTF-8'),
                         bcrypt.gensalt(10))


def checkpw(password, hashed_password):
    return bcrypt.hashpw(password.encode('UTF-8'),
                         hashed_password.encode('UTF-8')) == hashed_password
