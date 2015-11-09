"""Remove empty drafts

Revision ID: 410_remove_empty_drafts
Revises: 400_drop_agreement_returned
Create Date: 2015-11-09 11:41:00.000000

"""

# revision identifiers, used by Alembic.
revision = '410_remove_empty_drafts'
down_revision = '400_drop_agreement_returned'

from alembic import op


def upgrade():
    op.execute("""
        DELETE FROM draft_services WHERE (data->>'serviceName') is NULL;
    """)


def downgrade():
    pass
