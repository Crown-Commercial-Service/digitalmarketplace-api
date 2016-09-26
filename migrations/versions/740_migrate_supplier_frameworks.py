"""migrate supplier_frameworks to framework_agreements

Revision ID: 740
Revises: 730
Create Date: 2016-09-26 09:43:56.196966

For supplier_framework rows that contain details of returning a framework agreement (indicated
by non null `agreement_details` or `agreement_returned_at`) and do not yet have a
corresponding row in the `framework_agreements` table.

"""

# revision identifiers, used by Alembic.
revision = '740'
down_revision = '730'

from alembic import op


def upgrade():
    op.execute("""
        INSERT INTO framework_agreements(supplier_id, framework_id, signed_agreement_details, signed_agreement_returned_at)
        (SELECT sf.supplier_id, sf.framework_id, sf.agreement_details, sf.agreement_returned_at
            FROM supplier_frameworks sf
            LEFT JOIN framework_agreements fa
            ON sf.supplier_id = fa.supplier_id
            AND sf.framework_id = fa.framework_id
            WHERE fa.id IS NULL
            -- We need to convert JSON to text as JSON null is not the same as SQL null
            AND (sf.agreement_details::text != 'null' OR sf.agreement_returned_at IS NOT NULL)
        );
    """)


def downgrade():
    # No downgrade possible
    pass
