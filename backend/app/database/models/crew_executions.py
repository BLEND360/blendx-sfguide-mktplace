"""
Crew execution models for BlendX Core.

Defines Pydantic and SQLAlchemy models for tracking crew execution metadata, status, and relationships in the database.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.database.utils.enums import StatusEnum


class CrewExecutionCreate(BaseModel):
    """
    Pydantic model for creating a crew execution record.

    Fields:
        id: Unique identifier for the crew execution.
        status: Status of the execution (pending, completed, etc.).
        name: Name of the crew.
        input: Optional input data.
        output: Optional output data.
        context: Execution context as a dictionary.
        execution_group_id: Optional related execution group ID.
        flow_execution_id: Optional related flow execution ID.
    """

    id: str
    status: StatusEnum
    name: str
    input: Optional[str] | None = None
    output: Optional[str] | None = None
    context: dict = Field(None)
    execution_group_id: Optional[str] = None
    flow_execution_id: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"context": {"key": "value"}}}}


class CrewExecutionData(BaseModel):
    """
    Pydantic model for reading crew execution data.

    Fields:
        output: Optional output data.
        name: Name of the crew.
    """

    output: Optional[str] | None = None
    name: str


import uuid

from snowflake.sqlalchemy import VARIANT
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database.models import Base
from app.database.utils.enums import StatusEnum


class CrewExecution(Base):
    """
    SQLAlchemy model for the crew_executions table.

    Tracks crew execution status, input/output, context, and relationships to agent, execution group, and flow execution records.
    """

    __tablename__ = "crew_executions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    name = Column(String(255), nullable=True)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    context = Column(VARIANT, nullable=True)

    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())
    finished_at = Column(DateTime, nullable=True)

    agent_executions = relationship("AgentExecution", back_populates="crew_execution")

    execution_group_id = Column(
        String(36), ForeignKey("execution_groups.id"), nullable=True
    )
    execution_group = relationship(
        "ExecutionGroup",
        back_populates="crew_executions",
        foreign_keys=[execution_group_id],
    )

    flow_execution_id = Column(
        String(36), ForeignKey("flow_executions.id"), nullable=True
    )
    flow_execution = relationship(
        "FlowExecution",
        back_populates="crew_executions",
        foreign_keys=[flow_execution_id],
    )
