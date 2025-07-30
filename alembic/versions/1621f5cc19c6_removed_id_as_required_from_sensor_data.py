"""removed id as required from sensor data

Revision ID: 1621f5cc19c6
Revises: 689f53bef6c2
Create Date: 2025-07-30 12:55:01.785899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1621f5cc19c6'
down_revision: Union[str, None] = '689f53bef6c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
