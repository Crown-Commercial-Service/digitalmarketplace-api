"""Add terms acceptance column to User

Revision ID: 740
Revises: 730
Create Date: 2016-09-06 11:32:46.260079

"""

# revision identifiers, used by Alembic.
revision = '740'
down_revision = '730'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from app import models
    op.add_column('user', sa.Column('terms_accepted_at', sa.DateTime, nullable=True))
    UserTable = models.User.__table__
    op.execute(
        UserTable.update(). \
                where(UserTable.c.terms_accepted_at.is_(None)). \
                values({'terms_accepted_at': UserTable.c.created_at})
    )
    op.alter_column('user', 'terms_accepted_at', nullable=False)


def downgrade():
    op.drop_column('user', 'terms_accepted_at')
