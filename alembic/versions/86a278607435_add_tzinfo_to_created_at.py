"""add tzinfo to created_at

Revision ID: 86a278607435
Revises: cac48466329b
Create Date: 2025-03-13 15:20:49.221700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86a278607435'
down_revision: Union[str, None] = 'cac48466329b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # Update existing records: convert created_at to a timezone-aware timestamp assuming -07:00 offset
    op.execute(
        """
        ALTER TABLE "SensorData"
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE '-07:00';
        """
    )
    # Set default value for future inserts
    op.execute(
        """
        ALTER TABLE "SensorData"
        ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE '-07:00');
        """
    )

def downgrade():
    # Remove the default value
    op.execute(
        """
        ALTER TABLE "SensorData"
        ALTER COLUMN created_at DROP DEFAULT;
        """
    )
    # Revert the column type back to TIMESTAMP WITHOUT TIME ZONE
    op.execute(
        """
        ALTER TABLE "SensorData"
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
        USING created_at AT TIME ZONE 'UTC';
        """
    )