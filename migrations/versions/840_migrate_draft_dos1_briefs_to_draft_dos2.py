"""Migrate draft DOS1 briefs to draft DOS2 briefs

Revision ID: 840
Revises: 830
Create Date: 2017-02-07 15:31:50.715832

"""

# revision identifiers, used by Alembic.
revision = '840'
down_revision = '830'

from alembic import op

def upgrade():
    # Change framework of draft DOS1 briefs from DOS1 (framework_id == 5) to DOS2 (framework_id == 7)
    op.execute("""
        UPDATE briefs
        SET framework_id = 7
        WHERE framework_id = 5 AND published_at IS NULL
    """)


def downgrade():
    # No downgrade
    pass
