"""corrections to match model

Revision ID: b48fd3ae3d00
Revises: 880
Create Date: 2016-12-15 14:17:27.554023

"""

# revision identifiers, used by Alembic.
revision = '950'
down_revision = '940'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        create sequence "public"."product_id_seq";

        create table "public"."product" (
            "id" integer not null default nextval('product_id_seq'::regclass),
            "name" character varying not null,
            "pricing" character varying,
            "summary" character varying,
            "support" character varying,
            "website" character varying,
            "supplier_code" bigint not null
        );

        CREATE UNIQUE INDEX product_pkey ON product USING btree (id);

        alter table "public"."product" add constraint "product_pkey" PRIMARY KEY using index "product_pkey";

        alter table "public"."product" add constraint "product_supplier_code_fkey" FOREIGN KEY (supplier_code) REFERENCES supplier(code);
    """)


def downgrade():
    pass
