""" Cleanup

Revision ID: 830
Revises: 820
Create Date: 2016-10-11 15:18:01.489695

"""

# revision identifiers, used by Alembic.
revision = '830'
down_revision = '820'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("""
        alter table "public"."supplier" drop column "data_version";
        alter table "public"."supplier" add column "data" json;

        create sequence "public"."supplier_code_seq";
        alter table "public"."supplier" alter column "code" set default nextval('supplier_code_seq'::regclass);
    """)
    ### end Alembic commands ###

def downgrade():
    op.execute("""
        alter table "public"."supplier" add column "data_version" varchar;
        alter table "public"."supplier" drop column "data";

        alter table "public"."supplier" alter column "code" drop default;
        drop sequence if exists "public"."supplier_code_seq";
    """)
