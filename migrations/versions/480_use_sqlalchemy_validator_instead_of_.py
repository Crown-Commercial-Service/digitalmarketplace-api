"""Use SQLAlchemy validator instead of enum for framework

Revision ID: 480
Revises: 470
Create Date: 2016-01-29 15:47:25.481313

"""

# revision identifiers, used by Alembic.
revision = '480'
down_revision = '470'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        ALTER TABLE frameworks ALTER COLUMN framework
        TYPE character varying USING framework::character varying
    """)

    op.execute("""
        DROP TYPE framework_enum
    """)


def downgrade():
    op.execute("""
        CREATE TYPE framework_enum AS ENUM (
            'gcloud', 'dos'
        )
    """)

    op.execute("""
        ALTER TABLE frameworks ALTER COLUMN framework TYPE framework_enum
        USING framework::framework_enum
    """)
