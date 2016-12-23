"""finalized domains

Revision ID: b48fd3ae3d00
Revises: 860
Create Date: 2016-12-15 14:17:27.554023

"""

# revision identifiers, used by Alembic.
revision = '860'
down_revision = '850'

from alembic import op
import sqlalchemy as sa

import yaml
domainlist = yaml.load(open('data/domains.yaml'))


def upgrade():
    op.execute('alter table supplier_domain drop constraint "supplier_domain_domain_id_fkey"')
    op.execute('delete from domain;')
    op.execute('ALTER SEQUENCE domain_id_seq RESTART WITH 1;')
    op.execute('alter table domain add column ordering integer not null')
    conn = op.get_bind()

    for i, d in enumerate(domainlist):
        conn.execute(sa.text("""
            insert into
                domain (name, ordering)
            values
                (:domain, :ordering);
        """), domain=d, ordering=i+1)

    op.execute('alter table supplier_domain add constraint "supplier_domain_domain_id_fkey" FOREIGN KEY (domain_id) REFERENCES domain(id)')



def downgrade():
    op.execute('alter table domain drop column ordering')
