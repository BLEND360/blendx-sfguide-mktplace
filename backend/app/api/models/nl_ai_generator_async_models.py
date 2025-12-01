"""
Async Natural Language AI Generator API Models for BlendX Core.

Defines Pydantic models for the async NL generator API endpoints.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class NLAIGeneratorAsyncRequest(BaseModel):
    """
    Request model for the async NL generator endpoint.

    Fields:
        user_request: The user's natural language request for workflow generation.
        user_id: Optional user identifier for tracking and uniqueness checks.
    """

    user_request: str = Field(
        ...,
        description="Natural language description of desired AI workflow.",
        min_length=1,
        max_length=5000,
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user identifier for tracking purposes and title uniqueness.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_request": "Create a crew to analyze customer feedback and generate insights",
                "user_id": "user_123",
            }
        }
    }


class WorkflowData(BaseModel):
    """
    Workflow data model for responses.

    Fields:
        workflow_id: Unique identifier for the workflow.
        version: Version number of the workflow.
        type: Type of workflow (run-build-flow or run-build-crew).
        status: Current status of the workflow (PENDING, COMPLETED, FAILED).
        mermaid: Mermaid chart representation of the workflow.
        title: Short descriptive title for the workflow.
        rationale: Explanation of the workflow design and choices.
        yaml_text: YAML configuration text for the workflow.
        user_id: Associated user ID.
        model: LLM model used for generation.
        stable: Whether this is the stable version.
        created_at: Timestamp when the workflow was created.
        updated_at: Timestamp when the workflow was last updated.
    """

    workflow_id: str
    version: int
    type: Literal["run-build-flow", "run-build-crew"]
    status: Optional[str] = None
    mermaid: Optional[str] = None
    title: Optional[str] = None
    rationale: str
    yaml_text: str
    user_id: Optional[str] = None
    model: Optional[str] = None
    stable: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "version": 1,
                "type": "run-build-crew",
                "status": "COMPLETED",
                "mermaid": "graph TD\n    A[Research Agent] --> B[Analysis Task]",
                "title": "Customer Feedback Analysis Workflow",
                "rationale": "This crew analyzes customer feedback with specialized agents.",
                "yaml_text": "crew_name: Customer Feedback Analysis\nagents:\n  - name: Research Agent",
                "user_id": "user_123",
                "model": "claude-3-5-sonnet",
                "stable": True,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
            }
        }
    }


class NLAIGeneratorAsyncResponse(BaseModel):
    """
    Response model for the async NL generator endpoint.

    Fields:
        workflow_id: Unique identifier for the generated workflow.
        status: Current status of the workflow generation.
    """

    workflow_id: str
    status: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "PENDING",
            }
        }
    }


class WorkflowListResponse(BaseModel):
    """
    Response model for listing workflows.

    Fields:
        workflows: List of workflow data.
        total: Total number of workflows.
        limit: Applied limit (if any).
    """

    workflows: List[WorkflowData]
    total: int
    limit: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflows": [
                    {
                        "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                        "version": 1,
                        "type": "run-build-crew",
                        "title": "Customer Feedback Analysis",
                        "rationale": "Analyzes customer feedback...",
                        "created_at": "2024-01-01T12:00:00Z",
                    }
                ],
                "total": 1,
                "limit": None,
            }
        }
    }


class WorkflowGetResponse(BaseModel):
    """
    Response model for getting a single workflow.

    Fields:
        workflow: Workflow data if found.
        found: Whether the workflow was found.
    """

    workflow: Optional[WorkflowData] = None
    found: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow": {
                    "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                    "version": 1,
                    "type": "run-build-crew",
                    "title": "Customer Feedback Analysis",
                    "rationale": "Analyzes customer feedback...",
                    "created_at": "2024-01-01T12:00:00Z",
                },
                "found": True,
            }
        }
    }
