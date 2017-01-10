"""domain assessment status

Revision ID: b48fd3ae3d00
Revises: 880
Create Date: 2016-12-15 14:17:27.554023

"""

# revision identifiers, used by Alembic.
revision = '880'
down_revision = '870'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
      create type "public"."supplier_domain_status_enum" as enum (
          'unassessed',
          'assessed',
          'rejected'
      );

      alter table "public"."supplier_domain"
      add column status "supplier_domain_status_enum";

      update
          supplier_domain
      set
            status = 'assessed'
      where assessed = 't'::boolean;

      update
          supplier_domain
      set
            status = 'unassessed'
      where assessed != 't'::boolean;

      alter table "public"."supplier_domain"
      drop column assessed;

      alter table brief add column domain_id integer;

      alter table brief add constraint "brief_domain_id_fkey" foreign key (domain_id) references domain(id);
    """)


def downgrade():
    pass
