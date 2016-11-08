"""set submitted at for old brief responses

Revision ID: 770
Revises: 760
Create Date: 2016-10-25 11:10:53.245586

"""

# revision identifiers, used by Alembic.
revision = '770'
down_revision = '760'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
	op.execute("""
        UPDATE brief_responses 
		SET submitted_at = created_at
		WHERE submitted_at IS NULL
    """)


def downgrade():
	# No downgrade
	pass
