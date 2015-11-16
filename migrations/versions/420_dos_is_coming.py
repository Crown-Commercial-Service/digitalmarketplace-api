"""DOS is coming

Revision ID: 420
Revises: 410_remove_empty_drafts
Create Date: 2015-11-16 14:10:35.814066

"""

# revision identifiers, used by Alembic.
revision = '420'
down_revision = '410_remove_empty_drafts'

from alembic import op


def upgrade():
    op.execute("COMMIT")
    op.execute("ALTER TYPE framework_enum ADD VALUE IF NOT EXISTS 'dos' after 'gcloud'")

    conn = op.get_bind()
    res = conn.execute("SELECT * FROM frameworks WHERE slug = 'digital-outcomes-and-specialists'")
    results = res.fetchall()

    if not results:
        op.execute("""
            INSERT INTO frameworks (name, framework, status, slug)
                values('Digital Outcomes and Specialists', 'dos', 'coming', 'digital-outcomes-and-specialists')
        """)


def downgrade():
    op.execute("""
        DELETE FROM frameworks where slug='digital-outcomes-and-specialists'
    """)
