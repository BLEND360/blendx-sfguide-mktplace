"""
Crew API Models.

Pydantic models for crew execution endpoints.
"""

from pydantic import BaseModel


class CrewStartResponse(BaseModel):
    """Response model for crew start endpoint."""

    execution_id: str
    status: str
    message: str


class CrewStatusResponse(BaseModel):
    """Response model for crew status endpoint."""

    execution_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class CrewExecutionItem(BaseModel):
    """Item in executions list."""

    execution_id: str
    status: str
    execution_timestamp: str | None
    updated_at: str | None
    workflow_id: str | None = None


class CrewExecutionsResponse(BaseModel):
    """Response model for crew executions list."""

    executions: list[CrewExecutionItem]