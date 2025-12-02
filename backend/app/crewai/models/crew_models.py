"""
Crew Models

This module contains Pydantic models for validating crew configurations.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.crewai.models.enums import ProcessType


class CrewDefinition(BaseModel):
    """Configuration for a single crew definition"""

    name: str = Field(..., description="Crew name")
    process: ProcessType = Field(
        ProcessType.SEQUENTIAL, description="Crew process type"
    )
    verbose: Optional[bool] = Field(
        True, description="Whether to show detailed execution logs"
    )
    memory: Optional[bool] = Field(
        False, description="Whether to enable memory for agents"
    )
    max_rpm: Optional[int] = Field(
        None, description="Maximum requests per minute for rate limiting"
    )
    agents: List[str] = Field(..., description="List of agent roles for this crew")
    tasks: List[str] = Field(..., description="List of task names for this crew")
    manager: Optional[str] = Field(
        None, description="Manager agent role (required for hierarchical process)"
    )

    class Config:
        extra = "forbid"
