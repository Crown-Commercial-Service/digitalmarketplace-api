"""Rename selection_answers to supplier_frameworks

Declaration is the name we have settled on for the questions that
a supplier answers to get onto a framework. As there are more details
that we seem to need to hang on this relationship, such as whether
they've registered interest, this has been pulled out into a table
that more generally models the relationship between a supplier and
frameworks.

Revision ID: 310_rename_selection_answers
Revises: 300_make_g7_pending
Create Date: 2015-10-05 19:10:42.467269

"""

# revision identifiers, used by Alembic.
revision = '310_rename_selection_answers'
down_revision = '300_make_g7_pending'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # Copied from 150_add_selection_answers.py
    op.create_table(
        'supplier_frameworks',
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('declaration', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['framework_id'], ['frameworks.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.supplier_id'], ),
        sa.PrimaryKeyConstraint('supplier_id', 'framework_id')
    )
    op.execute("""
        INSERT INTO supplier_frameworks(supplier_id, framework_id, declaration)
        SELECT supplier_id, framework_id, question_answers FROM selection_answers
    """)


def downgrade():
    op.execute('DROP TABLE supplier_frameworks')
