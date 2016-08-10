"""empty message

Revision ID: 339de994d726
Revises: 690
Create Date: 2016-08-09 09:59:32.375205

"""

# revision identifiers, used by Alembic.
revision = '700'
down_revision = '690'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from app import models
    op.bulk_insert(models.Framework.__table__, [
        {'name': 'G-Cloud 6', 'framework': 'g-cloud', 'status': 'live', 'slug': 'g-cloud-6'},
        {'name': 'G-Cloud 4', 'framework': 'g-cloud', 'status': 'expired', 'slug': 'g-cloud-4'},
        {'name': 'G-Cloud 5', 'framework': 'g-cloud', 'status': 'live', 'slug': 'g-cloud-5'},
        {'name': 'G-Cloud 7', 'framework': 'g-cloud', 'status': 'pending', 'slug': 'g-cloud-7'},
        {'name': 'Digital Outcomes and Specialists', 'framework': 'dos', 'status': 'coming', 'slug': 'digital-outcomes-and-specialists'},
        {'name': 'Digital Service Professionals', 'framework': 'dsp', 'status': 'live', 'slug': 'digital-service-professionals'},
    ])

    op.bulk_insert(models.Lot.__table__, [
        {'slug': 'saas', 'name': 'Software as a Service', 'one_service_limit': 'false', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'paas', 'name': 'Platform as a Service', 'one_service_limit': 'false', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'iaas', 'name': 'Infrastructure as a Service', 'one_service_limit': 'false', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'scs', 'name': 'Specialist Cloud Services', 'one_service_limit': 'false', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'digital-outcomes', 'name': 'Digital outcomes', 'one_service_limit': 'true', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'digital-specialists', 'name': 'Digital specialists', 'one_service_limit': 'true', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'user-research-participants', 'name': 'User research participants', 'one_service_limit': 'true', 'data': {"unitSingular": "service", "unitPlural": "services"}},
        {'slug': 'user-research-studios', 'name': 'User research studios', 'one_service_limit': 'false', 'data': {"unitSingular": "lab", "unitPlural": "labs"}},
        {'slug': 'digital-professionals', 'name': 'Digital professionals', 'one_service_limit': 'false', 'data': {"unitSingular": "service", "unitPlural": "services"}},
    ])
    op.bulk_insert(models.FrameworkLot.__table__, [
        {'framework_id': 1, 'lot_id': 1},
        {'framework_id': 1, 'lot_id': 2},
        {'framework_id': 1, 'lot_id': 3},
        {'framework_id': 1, 'lot_id': 4},
        {'framework_id': 2, 'lot_id': 1},
        {'framework_id': 2, 'lot_id': 2},
        {'framework_id': 2, 'lot_id': 3},
        {'framework_id': 2, 'lot_id': 4},
        {'framework_id': 3, 'lot_id': 1},
        {'framework_id': 3, 'lot_id': 2},
        {'framework_id': 3, 'lot_id': 3},
        {'framework_id': 3, 'lot_id': 4},
        {'framework_id': 4, 'lot_id': 1},
        {'framework_id': 4, 'lot_id': 2},
        {'framework_id': 4, 'lot_id': 3},
        {'framework_id': 4, 'lot_id': 4},
        {'framework_id': 5, 'lot_id': 5},
        {'framework_id': 5, 'lot_id': 6},
        {'framework_id': 5, 'lot_id': 7},
        {'framework_id': 5, 'lot_id': 8},
        {'framework_id': 6, 'lot_id': 9},
    ])


def downgrade():
    pass
