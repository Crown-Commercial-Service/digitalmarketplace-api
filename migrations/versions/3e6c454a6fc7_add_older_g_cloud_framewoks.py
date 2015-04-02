"""Add older G-Cloud Framewoks

Revision ID: 3e6c454a6fc7
Revises: 3acf60608a7d
Create Date: 2015-04-02 15:31:57.243449

"""

# revision identifiers, used by Alembic.
revision = '3e6c454a6fc7'
down_revision = '3acf60608a7d'

from alembic import op
from sqlalchemy.sql import table, column
from sqlalchemy import String, Boolean
import sqlalchemy as sa

frameworks = table('frameworks',
                   column('name', String),
                   column('expired', Boolean)
)


def upgrade():
    op.execute(
        frameworks.insert(). \
        values({'name': op.inline_literal('G-Cloud 4'), 'expired': op.inline_literal(True)})
    )
    op.execute(
        frameworks.insert(). \
        values({'name': op.inline_literal('G-Cloud 5'), 'expired': op.inline_literal(False)})
    )


def downgrade():
    op.execute(
        frameworks.delete().where(frameworks.c.name == 'G-Cloud 4')
    )
    op.execute(
        frameworks.delete().where(frameworks.c.name == 'G-Cloud 5')
    )
