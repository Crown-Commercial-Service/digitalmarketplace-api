"""sf_allow_declaration_reuse_pop_default

populate defaults for supplier_frameworks.allow_declaration_reuse

Revision ID: 1300
Revises: 1290
Create Date: 2019-06-10 17:09:55.071202

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1300'
down_revision = '1290'


def upgrade():
    # populate defaults
    op.execute("UPDATE supplier_frameworks SET allow_declaration_reuse = true")


def downgrade():
    op.execute("UPDATE supplier_frameworks SET allow_declaration_reuse = NULL")
