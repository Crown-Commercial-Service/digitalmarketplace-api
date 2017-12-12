"""add direct award tables

Revision ID: 950
Revises: 940
Create Date: 2017-08-22 12:01:28.054240

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '950'
down_revision = '940'


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('direct_award_projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('locked_at', sa.DateTime(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('direct_award_projects_pkey'))
    )
    op.create_table('direct_award_project_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['direct_award_projects.id'], name=op.f('direct_award_project_users_project_id_fkey')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('direct_award_project_users_user_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('direct_award_project_users_pkey'))
    )
    op.create_index(op.f('ix_direct_award_project_users_project_id'), 'direct_award_project_users', ['project_id'], unique=False)
    op.create_index(op.f('ix_direct_award_project_users_user_id'), 'direct_award_project_users', ['user_id'], unique=False)
    op.create_table('direct_award_searches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('searched_at', sa.DateTime(), nullable=True),
    sa.Column('search_url', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('direct_award_searches_created_by_fkey')),
    sa.ForeignKeyConstraint(['project_id'], ['direct_award_projects.id'], name=op.f('direct_award_searches_project_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('direct_award_searches_pkey'))
    )
    op.create_index('idx_project_id_active', 'direct_award_searches', ['project_id', 'active'], unique=True, postgresql_where=sa.text('active'))
    op.create_index(op.f('ix_direct_award_searches_active'), 'direct_award_searches', ['active'], unique=False)
    op.create_index(op.f('ix_direct_award_searches_project_id'), 'direct_award_searches', ['project_id'], unique=False)
    op.create_table('direct_award_search_result_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('search_id', sa.Integer(), nullable=False),
    sa.Column('archived_service_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['archived_service_id'], ['archived_services.id'], name=op.f('direct_award_search_result_entries_archived_service_id_fkey')),
    sa.ForeignKeyConstraint(['search_id'], ['direct_award_searches.id'], name=op.f('direct_award_search_result_entries_search_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('direct_award_search_result_entries_pkey'))
    )
    op.create_index(op.f('ix_direct_award_search_result_entries_archived_service_id'), 'direct_award_search_result_entries', ['archived_service_id'], unique=False)
    op.create_index(op.f('ix_direct_award_search_result_entries_search_id'), 'direct_award_search_result_entries', ['search_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_direct_award_search_result_entries_search_id'), table_name='direct_award_search_result_entries')
    op.drop_index(op.f('ix_direct_award_search_result_entries_archived_service_id'), table_name='direct_award_search_result_entries')
    op.drop_table('direct_award_search_result_entries')
    op.drop_index(op.f('ix_direct_award_searches_project_id'), table_name='direct_award_searches')
    op.drop_index(op.f('ix_direct_award_searches_active'), table_name='direct_award_searches')
    op.drop_index('idx_project_id_active', table_name='direct_award_searches')
    op.drop_table('direct_award_searches')
    op.drop_index(op.f('ix_direct_award_project_users_user_id'), table_name='direct_award_project_users')
    op.drop_index(op.f('ix_direct_award_project_users_project_id'), table_name='direct_award_project_users')
    op.drop_table('direct_award_project_users')
    op.drop_table('direct_award_projects')
    # ### end Alembic commands ###
