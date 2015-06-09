from .. import db


def get_db_version():

    return db.engine.execute(
        "SELECT version_num FROM alembic_version"
    ).scalar()
