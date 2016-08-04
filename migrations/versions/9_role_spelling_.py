"""empty message

Revision ID: 9_role_spelling
Revises: 8_supplier_timestamps
Create Date: 2016-08-02 14:17:02.844293

"""

# revision identifiers, used by Alembic.
revision = '9_role_spelling'
down_revision = '8_supplier_timestamps'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from app import models
    SC = models.ServiceCategory.__table__
    op.execute(SC.update().\
            where(SC.c.name==op.inline_literal('Digital Transformation Advisors')).\
            values({'name': op.inline_literal('Digital Transformation Advisers')}))
    SR = models.ServiceRole.__table__
    op.execute(SR.update().\
            where(SR.c.name==op.inline_literal('Senior Digital Transformation Advisor')).\
            values({'name': op.inline_literal('Senior Digital Transformation Adviser')}))


def downgrade():
    from app import models
    SC = models.ServiceCategory.__table__
    op.execute(SC.update().\
            where(SC.c.name==op.inline_literal('Digital Transformation Advisers')).\
            values({'name': op.inline_literal('Digital Transformation Advisors')}))
    SR = models.ServiceRole.__table__
    op.execute(SR.update().\
            where(SR.c.name==op.inline_literal('Senior Digital Transformation Adviser')).\
            values({'name': op.inline_literal('Senior Digital Transformation Advisor')}))
