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
        result_text: Text result from the execution.
        raw_output: Raw output as a dictionary.
        error_message: Optional error message.
        metadata: Execution metadata as a dictionary.
        workflow_id: Optional related workflow ID.
        is_test: Flag for test executions.
    """

    id: str
    status: StatusEnum
    result_text: Optional[str] = None
    raw_output: Optional[dict] = Field(None)
    error_message: Optional[str] = None
    metadata: Optional[dict] = Field(None)
    workflow_id: Optional[str] = None
    is_test: bool = False

    model_config = {"json_schema_extra": {"example": {"metadata": {"key": "value"}}}}


class CrewExecutionData(BaseModel):
    """
    Pydantic model for reading crew execution data.

    Fields:
        result_text: Text result from the execution.
        status: Status of the execution.
    """

    result_text: Optional[str] = None
    status: str


import uuid

from snowflake.sqlalchemy import VARIANT
from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text, func
from sqlalchemy.orm import relationship

from app.database.models import Base
from app.database.utils.enums import StatusEnum


class CrewExecution(Base):
    """
    SQLAlchemy model for the crew_executions table.

    Tracks crew execution status, results, metadata, and relationships to workflows.
    """

    __tablename__ = "crew_executions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    execution_timestamp = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())
    raw_output = Column(VARIANT, nullable=True)
    result_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(VARIANT, nullable=True)
    workflow_id = Column(String(255), nullable=True)
    is_test = Column(Boolean, nullable=False, default=False)

    agent_executions = relationship("AgentExecution", back_populates="crew_execution")
