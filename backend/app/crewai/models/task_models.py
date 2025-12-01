"""
Task Models

This module contains Pydantic models for validating task configurations.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.crewai.models.tool_models import Tool


class TaskConfig(BaseModel):
    """Configuration for a single task"""

    name: str = Field(..., min_length=1, description="Task name")
    description: str = Field(..., min_length=1, description="Task description")
    agent: Optional[str] = Field(
        None,
        min_length=1,
        description="Agent role that will execute this task (optional)",
    )
    expected_output: str = Field(
        ..., min_length=1, description="Expected output description"
    )
    tools: Optional[List[Tool]] = Field(
        default_factory=list, description="Tools available for this task"
    )
    context: Optional[List[str]] = Field(
        default_factory=list,
        description="List of task names whose outputs will be used as context",
    )
    output_file: Optional[str] = Field(
        None, description="File path to save task output"
    )
    execution_number: Optional[int] = Field(
        None,
        description="Order in which this task should be executed (lower numbers execute first)",
    )

    class Config:
        extra = "forbid"
