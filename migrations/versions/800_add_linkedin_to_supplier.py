"""add linkedin to supplier

Revision ID: c6108e44a507
Revises: 790
Create Date: 2016-09-21 11:03:52.193666

"""

# revision identifiers, used by Alembic.
revision = '800'
down_revision = '790'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('supplier', sa.Column('linkedin', sa.String(), nullable=True))
    op.execute("""
        UPDATE supplier SET
            linkedin = url
        FROM
            (select supplier_id, url from supplier__extra_links
  inner join website_link on supplier__extra_links.website_link_id = website_link.id
where label = 'LinkedIn') as urls
        WHERE
            id = urls.supplier_id
    """)


def downgrade():
    op.drop_column('work_order', 'linkedin')
