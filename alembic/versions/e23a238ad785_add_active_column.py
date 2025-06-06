"""add active column

Revision ID: e23a238ad785
Revises: af0c79009f09
Create Date: 2025-03-13 12:15:55.726466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e23a238ad785'
down_revision: Union[str, None] = 'af0c79009f09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Sensors', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Sensors', 'active')
    # ### end Alembic commands ###
