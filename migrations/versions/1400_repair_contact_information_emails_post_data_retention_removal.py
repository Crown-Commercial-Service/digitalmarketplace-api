"""Replace '<removed>' with '<removed>@{uuid}.com'.format(uuid=str(uuid4())) in contact_information to pass validation.

Revision ID: 1400
Revises: 1390
Create Date: 2019-10-29 09:09:00.000000

"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '1400'
down_revision = '1390'


contact_information = table(
    'contact_information',
    column('id', sa.INTEGER),
    column('email', sa.VARCHAR),
)


def upgrade():
    """Update any contact_information rows where the email is set to '<removed>' to use the UUID email format we use
    on the user object in User.remove_personal_data

    Loop over the ids so we get a unique UUID for each update.
    """
    conn = op.get_bind()

    # SELECT id FROM contact_information WHERE email = '<removed>';
    query = contact_information.select().where(
        contact_information.c.email == '<removed>'
    ).with_only_columns(
        contact_information.c.id
    )

    ci_ids = (ci_id for ci_id, in conn.execute(query).fetchall())

    for ci_id in ci_ids:
        # UPDATE contact_information SET email = '<removed>@uuid-etc.com' WHERE id = <ci_id>;
        query = contact_information.update().where(
            contact_information.c.id == ci_id
        ).values(
            email='<removed>@{uuid}.com'.format(uuid=str(uuid4()))
        )

        conn.execute(query)


def downgrade():
    pass
