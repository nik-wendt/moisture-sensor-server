"""added battery_value

Revision ID: 689f53bef6c2
Revises: 370a509004a4
Create Date: 2025-04-01 23:32:46.898120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '689f53bef6c2'
down_revision: Union[str, None] = '370a509004a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('SensorData', sa.Column('battery_value', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('SensorData', 'battery_value')
