"""Add Outcome model

Revision ID: 1200
Revises: 1210
Create Date: 2018-05-10 17:22:50.773017

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1210'
down_revision = '1200'


def upgrade():
    op.create_unique_constraint('uq_brief_responses_id_brief_id', 'brief_responses', ['id', 'brief_id'])
    op.create_unique_constraint(
        'uq_direct_award_search_result_entries_archived_service_id_search_id',
        'direct_award_search_result_entries',
        ['archived_service_id', 'search_id'],
    )
    op.create_unique_constraint('uq_direct_award_searches_id_project_id', 'direct_award_searches', ['id', 'project_id'])
    op.create_table('outcomes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.BigInteger(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('awarding_organisation_name', sa.String(), nullable=True),
        sa.Column('award_value', sa.Numeric(precision=11, scale=2), nullable=True),
        sa.Column('result', sa.String(), nullable=False),
        sa.Column('direct_award_project_id', sa.Integer(), nullable=True),
        sa.Column('direct_award_search_id', sa.Integer(), nullable=True),
        sa.Column('direct_award_archived_service_id', sa.Integer(), nullable=True),
        sa.Column('brief_id', sa.Integer(), nullable=True),
        sa.Column('brief_response_id', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "CASE WHEN (result = 'awarded') THEN CAST(brief_response_id IS NULL AS BOOLEAN) = CAST(brief_id IS NULL AS BOOLEAN) ELSE CAST(brief_response_id IS NULL AS BOOLEAN) END",
            name=op.f('ck_outcomes_brief_keys_nullable'),
        ),
        sa.CheckConstraint(
            "CASE WHEN (result = 'awarded') THEN CAST(direct_award_project_id IS NULL AS BOOLEAN) = " \
            "CAST(direct_award_search_id IS NULL AS BOOLEAN) AND CAST(direct_award_project_id IS NULL AS BOOLEAN) = " \
            "CAST(direct_award_archived_service_id IS NULL AS BOOLEAN) ELSE " \
            "CAST(direct_award_search_id IS NULL AS BOOLEAN) " \
            "AND CAST(direct_award_archived_service_id IS NULL AS BOOLEAN) END",
            name=op.f('ck_outcomes_direct_award_keys_nullable'),
        ),
        sa.CheckConstraint(
            'CAST(direct_award_project_id IS NULL AS BOOLEAN) != CAST(brief_id IS NULL AS BOOLEAN)', name=op.f('ck_outcomes_either_brief_xor_direct_award'),
        ),
        sa.ForeignKeyConstraint(['brief_id'], ['briefs.id'], name=op.f('outcomes_brief_id_fkey')),
        sa.ForeignKeyConstraint(
            ['brief_response_id', 'brief_id'],
            ['brief_responses.id', 'brief_responses.brief_id'],
            name='fk_outcomes_brief_response_id_brief_id',
            initially='DEFERRED',
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ['brief_response_id'],
            ['brief_responses.id'],
            name=op.f('outcomes_brief_response_id_fkey'),
        ),
        sa.ForeignKeyConstraint(
            ['direct_award_archived_service_id', 'direct_award_search_id'],
            ['direct_award_search_result_entries.archived_service_id', 'direct_award_search_result_entries.search_id'],
            name='fk_outcomes_da_service_id_da_search_id',
            initially='DEFERRED',
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ['direct_award_archived_service_id'],
            ['archived_services.id'],
            name=op.f('outcomes_direct_award_archived_service_id_fkey'),
        ),
        sa.ForeignKeyConstraint(
            ['direct_award_project_id'],
            ['direct_award_projects.id'],
            name=op.f('outcomes_direct_award_project_id_fkey'),
        ),
        sa.ForeignKeyConstraint(
            ['direct_award_search_id', 'direct_award_project_id'],
            ['direct_award_searches.id', 'direct_award_searches.project_id'],
            name='fk_outcomes_da_search_id_da_project_id',
            initially='DEFERRED',
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ['direct_award_search_id'],
            ['direct_award_searches.id'],
            name=op.f('outcomes_direct_award_search_id_fkey'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('outcomes_pkey')),
        sa.UniqueConstraint('external_id', name=op.f('uq_outcomes_external_id')),
    )
    op.create_index(
        'idx_outcomes_completed_brief_unique',
        'outcomes',
        ['brief_id'],
        unique=True,
        postgresql_where=sa.text('completed_at IS NOT NULL'),
    )
    op.create_index(
        'idx_outcomes_completed_direct_award_project_unique',
        'outcomes',
        ['direct_award_project_id'],
        unique=True,
        postgresql_where=sa.text('completed_at IS NOT NULL'),
    )


def downgrade():
    op.drop_index('idx_outcomes_completed_direct_award_project_unique', table_name='outcomes')
    op.drop_index('idx_outcomes_completed_brief_unique', table_name='outcomes')
    op.drop_table('outcomes')
    op.drop_constraint('uq_direct_award_searches_id_project_id', 'direct_award_searches', type_='unique')
    op.drop_constraint(
        'uq_direct_award_search_result_entries_archived_service_id_search_id',
        'direct_award_search_result_entries',
        type_='unique',
    )
    op.drop_constraint('uq_brief_responses_id_brief_id', 'brief_responses', type_='unique')
