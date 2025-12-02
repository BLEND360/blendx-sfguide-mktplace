"""
Agent Configuration Model

This module contains the AgentConfig model for validating agent configurations.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.crewai.models.llm_models import LLMConfig
from app.crewai.models.tool_models import Tool


class AgentConfig(BaseModel):
    """Configuration for a single agent"""

    role: str = Field(..., min_length=1, description="Agent's role/title")
    goal: str = Field(..., min_length=1, description="Agent's primary goal")
    backstory: str = Field(..., min_length=1, description="Agent's background story")
    tools: Optional[List[Tool]] = Field(
        default_factory=list, description="List of tools available to the agent"
    )
    verbose: Optional[bool] = Field(
        True, description="Whether to enable verbose logging"
    )
    allow_delegation: Optional[bool] = Field(
        False, description="Whether agent can delegate tasks"
    )
    memory: Optional[bool] = Field(
        None, description="Whether to enable memory for this agent"
    )
    max_iter: Optional[int] = Field(
        None, description="Maximum number of iterations for agent execution"
    )
    max_rpm: Optional[int] = Field(
        None, description="Maximum requests per minute for rate limiting"
    )
    max_execution_time: Optional[int] = Field(
        None, description="Maximum execution time in seconds"
    )
    allow_code_execution: Optional[bool] = Field(
        False, description="Whether agent is allowed to execute code"
    )
    max_retry_limit: Optional[int] = Field(
        None, description="Maximum number of retry attempts"
    )
    llm: Optional[LLMConfig] = Field(
        None, description="LLM configuration for this agent"
    )

    class Config:
        extra = "forbid"
