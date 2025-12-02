"""
Workflow models for BlendX Core.

Defines Pydantic and SQLAlchemy models for tracking workflows (execution groups and flows)
generated through the natural language generator chat interface.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field
from snowflake.sqlalchemy import VARIANT
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text, func

from app.database.models import Base


class WorkflowCreate(BaseModel):
    """
    Pydantic model for creating a workflow record.

    Fields:
        workflow_id: Unique identifier for the workflow.
        version: Version number of the workflow.
        type: Type of workflow (run-build-flow or run-build-crew).
        mermaid: Mermaid chart representation of the workflow.
        rationale: Explanation of the workflow design and choices.
        yaml_text: YAML configuration text for the workflow.
        chat_id: Associated chat session ID.
        message_id: Associated message ID.
        user_id: Associated user ID.
        stable: Whether this is the stable version.
    """

    workflow_id: str
    version: int = 1
    type: Literal["run-build-flow", "run-build-crew"]
    mermaid: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = "PENDING"
    rationale: Optional[str] = None
    yaml_text: str
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    model: Optional[str] = None
    stable: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "version": 1,
                "type": "run-build-crew",
                "mermaid": "graph TD\n    A[Research Agent] --> B[Analysis Task]\n    B --> C[Report Generation]",
                "rationale": "This crew is designed to analyze customer feedback with specialized agents for data collection, sentiment analysis, and reporting.",
                "yaml_text": "crew_name: Customer Feedback Analysis\nagents:\n  - name: Research Agent\n    role: Data Collector",
                "chat_id": "123e4567-e89b-12d3-a456-426614174000",
                "message_id": "msg_123e4567-e89b-12d3-a456-426614174001",
                "user_id": "user_123",
                "stable": True,
            }
        }
    }


class WorkflowUpdate(BaseModel):
    """
    Pydantic model for updating a workflow record.

    Fields:
        workflow_id: Unique identifier for the workflow.
        version: Version number of the workflow.
        type: Type of workflow (run-build-flow or run-build-crew).
        mermaid: Mermaid chart representation of the workflow.
        rationale: Explanation of the workflow design and choices.
        yaml_text: YAML configuration text for the workflow.
        user_id: Associated user ID.
        stable: Whether this is the stable version.
    """

    workflow_id: str
    version: Optional[int] = None
    type: Optional[Literal["run-build-flow", "run-build-crew"]] = None
    mermaid: Optional[str] = None
    rationale: Optional[str] = None
    yaml_text: Optional[str] = None
    user_id: Optional[str] = None
    model: Optional[str] = None
    stable: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "version": 2,
                "type": "run-build-crew",
                "mermaid": "graph TD\n    A[Research Agent] --> B[Analysis Task]\n    B --> C[Report Generation]",
                "rationale": "Updated rationale with improved analysis capabilities.",
                "yaml_text": "crew_name: Enhanced Customer Feedback Analysis\nagents:\n  - name: Research Agent\n    role: Senior Data Collector",
                "user_id": "user_123",
                "stable": False,
            }
        }
    }


class WorkflowResponse(BaseModel):
    """
    Pydantic model for workflow response.

    Fields:
        workflow_id: Unique identifier for the workflow.
        version: Version number of the workflow.
        type: Type of workflow (run-build-flow or run-build-crew).
        mermaid: Mermaid chart representation of the workflow.
        rationale: Explanation of the workflow design and choices.
        yaml_text: YAML configuration text for the workflow.
        chat_id: Associated chat session ID.
        message_id: Associated message ID.
        user_id: Associated user ID.
        stable: Whether this is the stable version.
        created_at: Timestamp when the workflow was created.
        updated_at: Timestamp when the workflow was last updated.
    """

    workflow_id: str
    version: int
    type: Literal["run-build-flow", "run-build-crew"]
    mermaid: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = "PENDING"
    rationale: Optional[str] = None
    yaml_text: str
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    model: Optional[str] = None
    stable: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "version": 1,
                "type": "run-build-crew",
                "mermaid": "graph TD\n    A[Research Agent] --> B[Analysis Task]\n    B --> C[Report Generation]",
                "rationale": "This crew is designed to analyze customer feedback with specialized agents for data collection, sentiment analysis, and reporting.",
                "yaml_text": "crew_name: Customer Feedback Analysis\nagents:\n  - name: Research Agent\n    role: Data Collector",
                "chat_id": "123e4567-e89b-12d3-a456-426614174000",
                "message_id": "msg_123e4567-e89b-12d3-a456-426614174001",
                "user_id": "user_123",
                "stable": True,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
            }
        },
    }


class Workflow(Base):
    """
    SQLAlchemy model for workflows table.

    Stores execution groups and flows generated through the natural language generator,
    including their mermaid charts, rationale, and YAML configurations.
    """

    __tablename__ = "workflows"

    workflow_id = Column(String(255), primary_key=True, nullable=False)
    version = Column(Integer, primary_key=True, nullable=False, default=1)
    type = Column(
        Enum("run-build-flow", "run-build-crew", name="workflow_type"), nullable=False
    )
    mermaid = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")
    rationale = Column(Text, nullable=True)
    yaml_text = Column(Text, nullable=False)
    chat_id = Column(String(255), nullable=True)
    message_id = Column(String(255), nullable=True)
    user_id = Column(String(255), nullable=True)
    model = Column(String(100), nullable=True)
    stable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<Workflow(workflow_id='{self.workflow_id}', version={self.version}, type='{self.type}', stable={self.stable}, chat_id='{self.chat_id}')>"
