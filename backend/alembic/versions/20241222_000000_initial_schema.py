"""Initial schema - Create all tables

Revision ID: 001_initial
Revises:
Create Date: 2024-12-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from snowflake.sqlalchemy import VARIANT

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create execution_groups table (referenced by crew_executions)
    op.create_table(
        'execution_groups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )

    # Create flow_executions table (referenced by crew_executions)
    op.create_table(
        'flow_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )

    # Create crew_executions table
    op.create_table(
        'crew_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('execution_timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('raw_output', VARIANT(), nullable=True),
        sa.Column('result_text', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', VARIANT(), nullable=True),
        sa.Column('workflow_id', sa.String(255), nullable=True),
        sa.Column('is_test', sa.Boolean(), nullable=False, server_default='FALSE'),
    )

    # Create agent_executions table
    op.create_table(
        'agent_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('input', sa.Text(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('crew_execution_id', sa.String(36), sa.ForeignKey('crew_executions.id'), nullable=True),
    )

    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('workflow_id', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('mermaid', sa.Text(), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('yaml_text', sa.Text(), nullable=False),
        sa.Column('chat_id', sa.String(255), nullable=True),
        sa.Column('message_id', sa.String(255), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('stable', sa.Boolean(), nullable=False, server_default='TRUE'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.PrimaryKeyConstraint('workflow_id', 'version'),
    )

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('chat_id', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP()')),
    )

    # Note: Secondary indexes are not supported on standard Snowflake tables
    # (only on Hybrid Tables). Snowflake uses micro-partitioning for query optimization.


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key dependencies
    # Note: Index was removed (not supported on standard Snowflake tables)
    op.drop_table('chat_messages')
    op.drop_table('workflows')
    op.drop_table('agent_executions')
    op.drop_table('crew_executions')
    op.drop_table('flow_executions')
    op.drop_table('execution_groups')
