"""Populate ServiceCategory and ServiceRol

Revision ID: 1_price_schedule_data
Revises: 89ddbb590a4f
Create Date: 2016-07-19 15:48:20.814830

"""

# revision identifiers, used by Alembic.
revision = '1_price_schedule_data'
down_revision = '89ddbb590a4f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from app import models
    op.bulk_insert(models.ServiceCategory.__table__, [
        { 'id': 1, 'name': 'Product Management' },
        { 'id': 2, 'name': 'Business Analysis' },
        { 'id': 3, 'name': 'Delivery Management and Agile Coaching' },
        { 'id': 4, 'name': 'User Research' },
        { 'id': 5, 'name': 'Service Design and Interaction Design' },
        { 'id': 6, 'name': 'Technical Architecture, Development, Ethical Hacking and Web Operations' },
        { 'id': 7, 'name': 'Performance and Web Analytics' },
        { 'id': 8, 'name': 'Inclusive Design and Accessibility' },
        { 'id': 9, 'name': 'Digital Transformation Advisors' },
    ])
    op.bulk_insert(models.ServiceRole.__table__, [
        { 'id': 11, 'category_id': 1, 'name': 'Junior Product Manager' },
        { 'id': 12, 'category_id': 1, 'name': 'Senior Product Manager' },
        { 'id': 21, 'category_id': 2, 'name': 'Junior Business Analyst' },
        { 'id': 22, 'category_id': 2, 'name': 'Senior Business Analyst' },
        { 'id': 31, 'category_id': 3, 'name': 'Junior Delivery Manager' },
        { 'id': 32, 'category_id': 3, 'name': 'Senior Delivery Manager' },
        { 'id': 33, 'category_id': 3, 'name': 'Senior Agile Coach' },
        { 'id': 41, 'category_id': 4, 'name': 'Senior User Research' },
        { 'id': 51, 'category_id': 5, 'name': 'Senior Service Designer' },
        { 'id': 52, 'category_id': 5, 'name': 'Junior Interaction Designer' },
        { 'id': 53, 'category_id': 5, 'name': 'Senior Interaction Designer' },
        { 'id': 61, 'category_id': 6, 'name': 'Senior Technical Lead' },
        { 'id': 62, 'category_id': 6, 'name': 'Junior Developer' },
        { 'id': 63, 'category_id': 6, 'name': 'Senior Developer' },
        { 'id': 64, 'category_id': 6, 'name': 'Junior Ethical Hacker' },
        { 'id': 65, 'category_id': 6, 'name': 'Senior Ethical Hacker' },
        { 'id': 66, 'category_id': 6, 'name': 'Junior Web Devops Engineer' },
        { 'id': 67, 'category_id': 6, 'name': 'Senior Web Devops Engineer' },
        { 'id': 71, 'category_id': 7, 'name': 'Junior Web Performance Analyst' },
        { 'id': 72, 'category_id': 7, 'name': 'Senior Web Performance Analyst' },
        { 'id': 81, 'category_id': 8, 'name': 'Junior Inclusive Designer (accessibility consultant)' },
        { 'id': 82, 'category_id': 8, 'name': 'Senior Inclusive Designer (accessibility consultant)' },
        { 'id': 91, 'category_id': 9, 'name': 'Senior Digital Transformation Advisor' },
    ])


def downgrade():
    pass
