"""Add framework slug

Revision ID: 150_add_framework_slug
Revises: 140_add_selection_questions
Create Date: 2015-06-19 16:24:33.894377

"""

# revision identifiers, used by Alembic.
revision = '150_add_framework_slug'
down_revision = '140_add_selection_questions'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('frameworks', sa.Column('slug', sa.String(), nullable=True))

    for i in range(4, 8):
        op.execute("UPDATE frameworks SET slug='g-cloud-{0}' WHERE name='G-Cloud {0}';".format(i))

    op.alter_column('frameworks', 'slug', nullable=False)
    op.create_index(op.f('ix_frameworks_slug'), 'frameworks', ['slug'], unique=True)


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_frameworks_slug'), table_name='frameworks')
    op.drop_column('frameworks', 'slug')
    ### end Alembic commands ###
