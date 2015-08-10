"""empty message

Revision ID: 220_rename_companies_house_id
Revises: 210_allow_null_postcodes
Create Date: 2015-08-09 09:27:05.848655

"""

# revision identifiers, used by Alembic.
revision = '220_rename_companies_house_id'
down_revision = '210_allow_null_postcodes'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute('alter table suppliers rename companies_house_id to companies_house_number')



def downgrade():
    op.execute('alter table suppliers rename companies_house_number to companies_house_id')
