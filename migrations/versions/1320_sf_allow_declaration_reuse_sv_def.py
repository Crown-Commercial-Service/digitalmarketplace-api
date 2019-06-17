"""sf_allow_declaration_reuse_sv_def



Revision ID: 1320
Revises: 1310
Create Date: 2019-06-17 16:07:25.688384

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1320'
down_revision = '1310'


def upgrade():
    op.alter_column(
        'supplier_frameworks',
        'allow_declaration_reuse',
        server_default='true',
    )


def downgrade():
    op.alter_column(
        'supplier_frameworks',
        'allow_declaration_reuse',
        server_default=None,
    )
