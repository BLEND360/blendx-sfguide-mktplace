"""
Database models package for BlendX Core.

Provides the SQLAlchemy declarative base class for all ORM models.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models to ensure they are registered with the Base metadata
# This is required for Alembic to detect all models for migrations
from app.database.models.workflows import Workflow
from app.database.models.crew_executions import CrewExecution
from app.database.models.chat_messages import ChatMessage
from app.database.models.execution_groups import ExecutionGroup
from app.database.models.flow_executions import FlowExecution
from app.database.models.agent_executions import AgentExecution

__all__ = [
    "Base",
    "Workflow",
    "CrewExecution",
    "ChatMessage",
    "ExecutionGroup",
    "FlowExecution",
    "AgentExecution",
]
