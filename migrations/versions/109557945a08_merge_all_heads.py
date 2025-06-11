"""merge all heads

Revision ID: 109557945a08
Revises: 02b69243af1d, 971e4766783d, f3a4b5c6d7e8
Create Date: 2025-06-10 14:24:16.183709

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '109557945a08'
down_revision = ('02b69243af1d', '971e4766783d', 'f3a4b5c6d7e8')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
