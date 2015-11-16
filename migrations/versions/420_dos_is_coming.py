"""DOS is coming

Revision ID: 420
Revises: 410_remove_empty_drafts
Create Date: 2015-11-16 14:10:35.814066

"""

# revision identifiers, used by Alembic.
revision = '420'
down_revision = '410_remove_empty_drafts'

from alembic import op
import sqlalchemy as sa
from app.models import Framework


def upgrade():
    op.execute("COMMIT")
    op.execute("ALTER TYPE framework_enum ADD VALUE IF NOT EXISTS 'dos' after 'gcloud'")

    framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()

    if not framework:
        op.execute("""
            INSERT INTO frameworks (name, framework, status, slug)
                values('Digital Outcomes and Specialists', 'dos', 'coming', 'digital-outcomes-and-specialists')
        """)


def downgrade():
    op.execute("""
        DELETE FROM frameworks where slug='digital-outcomes-and-specialists'
    """)
