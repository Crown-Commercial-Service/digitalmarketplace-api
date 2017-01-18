"""domain assessment id

Revision ID: b48fd3ae3d00
Revises: 880
Create Date: 2016-12-15 14:17:27.554023

"""

# revision identifiers, used by Alembic.
revision = '900'
down_revision = '890'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
      create sequence "public"."supplier_domain_id_seq";

      alter table "public"."supplier_domain"
      add column id INTEGER DEFAULT nextval('supplier_domain_id_seq'::regclass);
    """)


def downgrade():
    pass
