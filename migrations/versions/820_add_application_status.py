""" Add application table and applicant user role

Revision ID: 820
Revises: 810
Create Date: 2016-10-11 15:18:01.489695

"""

# revision identifiers, used by Alembic.
revision = '820'
down_revision = '810'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("""
        create type "public"."supplier_status_enum" as enum (
            'limited',
            'complete',
            'deleted'
        );

        create type "public"."application_status_enum" as enum (
            'saved',
            'submitted',
            'approved',
            'complete',
            'approval_rejected',
            'assessment_rejected'
        );

        alter table "public"."application" add column "status" varchar;
        alter table "public"."application" add column "supplier_code" bigint;
        alter table "public"."supplier" add column "status" varchar;



    """)

    ### end Alembic commands ###

def downgrade():
    op.execute("""
        alter table "public"."application" drop column "status";
        alter table "public"."application" drop column "supplier_code";
        alter table "public"."supplier" drop column "status";

        drop type "public"."supplier_status_enum";
        drop type "public"."application_status_enum";
    """)
