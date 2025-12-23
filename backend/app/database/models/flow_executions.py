"""
Flow execution models for BlendX Core.

Defines SQLAlchemy model for tracking flow executions which orchestrate crews in a flow.
"""

import uuid

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.orm import relationship

from app.database.models import Base
from app.database.utils.enums import StatusEnum


class FlowExecution(Base):
    """
    SQLAlchemy model for the flow_executions table.

    Represents the execution of a flow, which orchestrates multiple crews
    in a defined sequence or pattern (e.g., sequential, parallel, conditional).
    """

    __tablename__ = "flow_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=True)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    finished_at = Column(DateTime, nullable=True)

    crew_executions = relationship("CrewExecution", back_populates="flow_execution")

    def __repr__(self):
        return f"<FlowExecution(id='{self.id}', name='{self.name}', status='{self.status}')>"
