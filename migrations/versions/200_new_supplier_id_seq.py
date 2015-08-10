"""empty message

Revision ID: 200_new_supplier_id_seq
Revises: 190_add_companies_house_id
Create Date: 2015-08-06 09:46:13.467484

"""

# revision identifiers, used by Alembic.
revision = '200_new_supplier_id_seq'
down_revision = '190_add_companies_house_id'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute('create sequence suppliers_supplier_id_seq start 700000;')
    op.execute("alter table suppliers alter column supplier_id set default nextval('suppliers_supplier_id_seq')")


def downgrade():
    op.execute('alter table suppliers alter column supplier_id set default null');
    op.execute('drop sequence suppliers_supplier_id_seq;')
