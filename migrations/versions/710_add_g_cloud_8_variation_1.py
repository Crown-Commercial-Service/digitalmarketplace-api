"""Add g-cloud-8 variation 1

Revision ID: 710
Revises: 700
Create Date: 2016-08-19 16:11:38.493586

"""

# revision identifiers, used by Alembic.
revision = '710'
down_revision = '700'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("""
        UPDATE frameworks SET
            framework_agreement_details =
            '{"frameworkAgreementVersion": "v1.0", "variations":{"1":{"createdAt":"2016-08-19T15:31:00.000000Z"}}}'::json
        WHERE slug = 'g-cloud-8'
    """)


def downgrade():
    op.execute("""
        UPDATE frameworks SET
            framework_agreement_details = '{"frameworkAgreementVersion": "v1.0"}'::json
        WHERE slug = 'g-cloud-8'
    """)
