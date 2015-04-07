"""Set G6 services to be published rather than enabled

Revision ID: 3a5eba38e4e8
Revises: 3e6c454a6fc7
Create Date: 2015-04-02 16:18:30.609595

"""

# revision identifiers, used by Alembic.
revision = '3a5eba38e4e8'
down_revision = '3e6c454a6fc7'

from alembic import op
from sqlalchemy.sql import column, table
from sqlalchemy import String
import sqlalchemy as sa

services = table('services', column('status', String))


def upgrade():
    op.execute(
        services.update(). \
        values({'status': op.inline_literal('published')})
    )


def downgrade():
    op.execute(
        services.update(). \
        where(services.c.status == 'published'). \
        values({'status': op.inline_literal('enabled')})
    )
