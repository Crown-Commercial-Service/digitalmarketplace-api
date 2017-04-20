"""Add g-cloud-8 variation 1 countersigner details

Revision ID: 760
Revises: 750
Create Date: 2016-09-25 13:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = '760'
down_revision = '750'

from alembic import op


def upgrade():
    op.execute(
        "UPDATE frameworks SET framework_agreement_details = '"
        '{"frameworkAgreementVersion":"v1.0", '
        '"variations":{"1":'
        '{"createdAt":"2016-08-19T15:31:00.000000Z", '
        '"countersignedAt":"2016-10-05T11:00:00.000000Z", '
        '"countersignedByName":"Dan Saxby", '
        '"countersignedByRole":"Category Director"'
        "}}}'::json "
        "WHERE slug = 'g-cloud-8'"
    )


def downgrade():
    op.execute("""
        UPDATE frameworks SET
            framework_agreement_details =
            '{"frameworkAgreementVersion":"v1.0", "variations":{"1":{"createdAt":"2016-08-19T15:31:00.000000Z"}}}'::json
        WHERE slug = 'g-cloud-8'
    """)
