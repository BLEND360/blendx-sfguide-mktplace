"""
LLM Models

This module contains Pydantic models for validating LLM configurations
used in agent definitions.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.crewai.models.enums import LLMProvider


class LLMConfig(BaseModel):
    """LLM configuration for agents"""

    provider: LLMProvider = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    temperature: Optional[float] = Field(
        0.7, ge=0.0, le=2.0, description="Temperature for generation"
    )
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens for generation"
    )
    api_key: Optional[str] = Field(
        None, description="API key (will be loaded from environment)"
    )
