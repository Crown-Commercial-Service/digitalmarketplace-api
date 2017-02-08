"""corrections to match model

Revision ID: b48fd3ae3d00
Revises: 880
Create Date: 2016-12-15 14:17:27.554023

"""

# revision identifiers, used by Alembic.
revision = '930'
down_revision = '920'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        alter table "public"."supplier_user_invite_log" drop constraint "supplier_user_invite_log_supplier_id_fkey";

        alter table "public"."supplier_user_invite_log" drop constraint "supplier_user_invite_log_supplier_id_fkey1";

        alter table "public"."signed_agreement" drop constraint "signed_agreement_pkey";

        drop index if exists "public"."signed_agreement_pkey";

        alter table "public"."signed_agreement" drop column "id";

        alter table "public"."supplier_domain" alter column "status" set not null;

        drop sequence if exists "public"."signed_agreement_id_seq";

        CREATE UNIQUE INDEX alembic_version_pkc ON alembic_version USING btree (version_num);

        CREATE UNIQUE INDEX ix_supplier_domain_id ON supplier_domain USING btree (id);

        CREATE UNIQUE INDEX signed_agreement_pkey ON signed_agreement USING btree (agreement_id, user_id, application_id);

        alter table "public"."alembic_version" add constraint "alembic_version_pkc" PRIMARY KEY using index "alembic_version_pkc";

        alter table "public"."signed_agreement" add constraint "signed_agreement_pkey" PRIMARY KEY using index "signed_agreement_pkey";

        alter table "public"."supplier_user_invite_log" add constraint "supplier_user_invite_log_supplier_id_fkey" FOREIGN KEY (supplier_id, contact_id) REFERENCES supplier__contact(supplier_id, contact_id) ON DELETE CASCADE;

        alter table "public"."supplier_user_invite_log" add constraint "supplier_user_invite_log_supplier_id_fkey1" FOREIGN KEY (supplier_id) REFERENCES supplier(id) ON DELETE CASCADE;
    """)

    # remove character length constraints on columns
    op.execute("""
        alter table "public"."address" alter column "postal_code" set data type character varying;

        alter table "public"."framework" alter column "name" set data type character varying;

        alter table "public"."service_category" alter column "abbreviation" set data type character varying;

        alter table "public"."service_role" alter column "abbreviation" set data type character varying;

        alter table "public"."supplier" alter column "abn" set data type character varying;

        alter table "public"."supplier" alter column "acn" set data type character varying;

        alter table "public"."supplier" alter column "long_name" set data type character varying;

        alter table "public"."supplier" alter column "name" set data type character varying;

        alter table "public"."supplier" alter column "summary" set data type character varying;

        alter table "public"."supplier" alter column "website" set data type character varying;
    """)



def downgrade():
    pass
