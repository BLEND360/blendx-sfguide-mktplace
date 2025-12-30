"""
Execution group models for BlendX Core.

Defines SQLAlchemy model for tracking execution groups which organize multiple crew executions.
"""

import uuid

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.orm import relationship

from app.database.models import Base
from app.database.utils.enums import StatusEnum


class ExecutionGroup(Base):
    """
    SQLAlchemy model for the execution_groups table.

    Represents a logical grouping of crew executions, allowing multiple crews
    to be executed as part of a single workflow or batch operation.
    """

    __tablename__ = "execution_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    result = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    finished_at = Column(DateTime, nullable=True)


    def __repr__(self):
        return f"<ExecutionGroup(id='{self.id}', name='{self.name}', status='{self.status}')>"
