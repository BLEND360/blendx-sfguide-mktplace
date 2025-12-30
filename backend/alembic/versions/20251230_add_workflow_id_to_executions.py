"""add_workflow_id_and_result_to_executions

Revision ID: a1b2c3d4e5f6
Revises: bdeeff6c3dc1
Create Date: 2025-12-30 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'bdeeff6c3dc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add workflow_id and result columns to flow_executions
    op.add_column('flow_executions', sa.Column('workflow_id', sa.String(length=255), nullable=True))
    op.add_column('flow_executions', sa.Column('result', sa.Text(), nullable=True))

    # Add workflow_id and result columns to execution_groups
    op.add_column('execution_groups', sa.Column('workflow_id', sa.String(length=255), nullable=True))
    op.add_column('execution_groups', sa.Column('result', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns from execution_groups
    op.drop_column('execution_groups', 'result')
    op.drop_column('execution_groups', 'workflow_id')

    # Remove columns from flow_executions
    op.drop_column('flow_executions', 'result')
    op.drop_column('flow_executions', 'workflow_id')
