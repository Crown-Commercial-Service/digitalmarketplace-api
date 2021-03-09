"""Add deleted service status

Revision ID: 1460
Revises: 1450
Create Date: 2021-03-09 08:35:41.713530

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '1460'
down_revision = '1450'


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("""
            ALTER TABLE services
                DROP CONSTRAINT ck_services_status,
                ADD CONSTRAINT ck_services_status CHECK(status::text = ANY(ARRAY['disabled', 'enabled', 'published', 'deleted']));
        """)
        op.execute("""
            ALTER TABLE archived_services
                DROP CONSTRAINT ck_archived_services_status,
                ADD CONSTRAINT ck_archived_services_status CHECK(status::text = ANY(ARRAY['disabled', 'enabled', 'published', 'deleted']));
        """)

def downgrade():
    with op.get_context().autocommit_block():
        op.execute("""
            ALTER TABLE services
                DROP CONSTRAINT ck_services_status,
                ADD CONSTRAINT ck_services_status CHECK(status::text = ANY(ARRAY['disabled', 'enabled', 'published']));
        """)
        op.execute("""
            ALTER TABLE archived_services
                DROP CONSTRAINT ck_archived_services_status,
                ADD CONSTRAINT ck_archived_services_status CHECK(status::text = ANY(ARRAY['disabled', 'enabled', 'published']));
        """)
