"""Use SQLAlchemy validator instead of enum for framework status

Revision ID: 370
Revises: 360_add_pass_fail_returned
Create Date: 2015-10-29 13:44:17.371767

"""

# revision identifiers, used by Alembic.
revision = '370_use_sqlalchemy_validator'
down_revision = '360_add_pass_fail_returned'

from alembic import op
import sqlalchemy as sa


def upgrade():

    op.execute("""
        ALTER TABLE frameworks ALTER COLUMN status
        TYPE character varying USING status::character varying
    """)

    op.execute("""
        ALTER TABLE frameworks ALTER COLUMN status DROP DEFAULT
    """)

    op.execute("""
        DROP TYPE framework_status_enum
    """)


def downgrade():

    op.execute("""
        CREATE TYPE framework_status_enum AS ENUM (
            'coming', 'open', 'pending', 'standstill', 'live', 'expired'
        )
    """)

    op.execute("""
        ALTER TABLE frameworks ALTER COLUMN status TYPE framework_status_enum
        USING status::framework_status_enum
    """)

    op.execute("""
        ALTER TABLE frameworks ALTER COLUMN status SET DEFAULT 'pending'
    """)
