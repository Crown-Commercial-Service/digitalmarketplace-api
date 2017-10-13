"""Migrate buyer email domains from .txt file to DB

Revision ID: 1030
Revises: 1020
Create Date: 2017-10-13 11:18:22.683693

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1030'
down_revision = '1020'

buyer_domains_table = sa.Table(
    'buyer_email_domains',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('domain_name', sa.String, nullable=True),
)


def upgrade():
    try:
        with open('./data/buyer-email-domains.txt') as f:
            legacy_buyer_domains = [line.strip() for line in f]
    except FileNotFoundError as e:
        # Once we have deleted the file, we can exit the migration early
        return

    conn = op.get_bind()
    for legacy_domain in legacy_buyer_domains:
        # SELECT domain_name FROM buyer_email_domains WHERE domain_name == 'legacy-domain.org'
        query = buyer_domains_table.select(buyer_domains_table.c.domain_name == legacy_domain)

        result = conn.execute(query).first()
        if not result:
            # INSERT INTO buyer_email_domains (domain_name) VALUES ("legacy-domain.org");
            query = buyer_domains_table.insert().values(domain_name=legacy_domain)
            conn.execute(query)


def downgrade():
    pass
