"""Migrate draft DOS1 briefs to draft DOS2 briefs

Revision ID: 840
Revises: 830
Create Date: 2017-02-07 15:31:50.715832

"""

# revision identifiers, used by Alembic.
revision = '840'
down_revision = '830'

from alembic import op
from sqlalchemy.sql import text

def upgrade():
    conn = op.get_bind()

    dos1_res = conn.execute("""
        SELECT id FROM frameworks
        WHERE name = 'Digital Outcomes and Specialists'
    """)
    dos1_framework_id = dos1_res.fetchall()[0][0]

    dos2_res = conn.execute("""
        SELECT id FROM frameworks
        WHERE name = 'Digital Outcomes and Specialists 2'
    """)

    # DOS2 framework was not created with a migration, it was created via the API. This means that when the tests run
    # and set up the test database by running the migrations, there is no DOS2 framework to query to find it's ID. The
    # following check will bail out of the migration if this is the case.
    query_results = dos2_res.fetchall()
    if not query_results:
        return

    dos2_framework_id = query_results[0][0]

    framework_ids = {
        "dos1_id": dos1_framework_id,
        "dos2_id": dos2_framework_id
    }

    conn.execute(text("""
        UPDATE briefs
        SET framework_id = :dos2_id
        WHERE framework_id = :dos1_id AND published_at IS NULL
    """), **framework_ids)


def downgrade():
    # No downgrade
    pass
