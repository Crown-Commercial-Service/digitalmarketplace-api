"""Add an index to audit events data blob to make it easier to search by supplier id. The data needed to be converted
to JSONB from JSON for the index to work. It's a partial index - so only indexing rows that have the 'supplierId' field
in their data blob. It's also an expression index, so only indexing the 'supplierId' field rather than all of the data.

Revision ID: 1260
Revises: 1250
Create Date: 2018-08-13 11:54:17.725685

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '1260'
down_revision = '1250'


def upgrade():
    op.alter_column('audit_events', 'data', type_=JSONB, postgresql_using='data::text::jsonb')
    op.create_index(
        'idx_audit_events_data_supplier_id',
        'audit_events',
        [sa.text("COALESCE((data ->> 'supplierId'), (data ->> 'supplier_id'))")],
        unique=False,
        postgresql_where=sa.text("COALESCE(data ->> 'supplierId', data ->> 'supplier_id') IS NOT NULL"),
    )


def downgrade():
    op.drop_index('idx_audit_events_data_supplier_id', table_name='audit_events')
