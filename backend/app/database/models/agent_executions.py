"""
Agent execution models for BlendX Core.

Defines SQLAlchemy model for tracking individual agent executions within a crew.
"""

import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship

from app.database.models import Base
from app.database.utils.enums import StatusEnum


class AgentExecution(Base):
    """
    SQLAlchemy model for the agent_executions table.

    Tracks individual agent execution status, input/output, and relationship
    to the parent crew execution.
    """

    __tablename__ = "agent_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=True)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    finished_at = Column(DateTime, nullable=True)

    crew_execution_id = Column(
        String(36), ForeignKey("crew_executions.id"), nullable=True
    )
    crew_execution = relationship(
        "CrewExecution",
        back_populates="agent_executions",
        foreign_keys=[crew_execution_id],
    )

    def __repr__(self):
        return f"<AgentExecution(id='{self.id}', name='{self.name}', status='{self.status}')>"
