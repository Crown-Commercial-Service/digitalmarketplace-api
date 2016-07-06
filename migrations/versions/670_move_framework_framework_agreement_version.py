"""Move Framework.framework_agreement_version into new framework_agreement_details json field

Revision ID: 670
Revises: 660
Create Date: 2016-06-29 11:54:27.719038

"""

# revision identifiers, used by Alembic.
revision = '670'
down_revision = '660'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('frameworks', sa.Column('framework_agreement_details', postgresql.JSON(), nullable=True))
    op.execute("""
        UPDATE frameworks SET
            -- using to_json to ensure framework_agreement_version gets properly escaped for json
            framework_agreement_details = (
                '{"frameworkAgreementVersion":' || to_json(framework_agreement_version) || '}'
            )::json
        WHERE
            framework_agreement_version IS NOT NULL and framework_agreement_version != ''
    """)
    op.drop_column('frameworks', 'framework_agreement_version')


def downgrade():
    op.add_column('frameworks', sa.Column('framework_agreement_version', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.execute("""
        UPDATE frameworks SET
            framework_agreement_version = framework_agreement_details->>'frameworkAgreementVersion'
    """)
    op.drop_column('frameworks', 'framework_agreement_details')
