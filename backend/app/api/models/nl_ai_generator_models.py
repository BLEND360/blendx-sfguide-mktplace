from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MermaidChartResponse(BaseModel):
    """Structured output model for mermaid chart generation."""

    mermaid_chart: str = Field(
        ...,
        description="Valid Mermaid flowchart code representing the CrewAI workflow. "
        "Must include title, flowchart LR direction, proper node definitions, "
        "connections with labels, and pastel color class definitions.",
    )


class NLAIGeneratorRequest(BaseModel):
    user_request: str = Field(
        ..., description="User's natural language request for YAML generation."
    )


class NLAIGeneratorResponse(BaseModel):
    payload: dict = Field(
        ..., description="JSON object configuration for CrewAI (flow or group)"
    )
    type: Literal["run-build-flow", "run-build-crew"] = Field(
        ..., description="Type of execution: flow or group"
    )
    rationale: str = Field(..., description="Rationale for the design and choices made")
    mermaid_chart: Optional[str] = Field(
        None, description="Mermaid chart representing the YAML config visually."
    )
    model: Optional[str] = Field(None, description="LLM model used for generation")
    classification_reasoning: Optional[str] = Field(
        None, description="Reasoning for workflow type classification (V2 only)"
    )
    classification_confidence: Optional[str] = Field(
        None,
        description="Confidence level of classification: high, medium, or low (V2 only)",
    )
