"""Drop selection_answers table

Revision ID: 320_drop_selection_answers
Revises: 310_rename_selection_answers
Create Date: 2015-10-14 10:52:26.557319

"""

# revision identifiers, used by Alembic.
revision = '320_drop_selection_answers'
down_revision = '310_rename_selection_answers'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.execute('DROP TABLE selection_answers')


def downgrade():
    op.create_table(
        'selection_answers',
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('question_answers', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['framework_id'], ['frameworks.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.supplier_id'], ),
        sa.PrimaryKeyConstraint('supplier_id', 'framework_id')
    )
    op.execute("""
        INSERT INTO selection_answers(supplier_id, framework_id, question_answers)
        SELECT supplier_id, framework_id, declaration FROM supplier_frameworks
    """)
