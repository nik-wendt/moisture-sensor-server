"""removed id as required from sensor data 2

Revision ID: c39d1f45fd2f
Revises: 1621f5cc19c6
Create Date: 2025-07-30 13:21:40.366850

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c39d1f45fd2f"
down_revision: Union[str, None] = "1621f5cc19c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the FK constraint
    op.drop_constraint(
        constraint_name="fk_child_parent_id_parent",  # your FK constraint name
        table_name="SensorData",
        type_="foreignkey",
    )

    # 2. Alter the column to be nullable
    op.alter_column(
        table_name="SensorData",
        column_name="sensor_id",
        existing_type=sa.Integer(),  # adjust to your column's actual type
        nullable=True,
    )


def downgrade() -> None:
    pass
