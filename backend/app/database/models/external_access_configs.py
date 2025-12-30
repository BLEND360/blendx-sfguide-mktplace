"""
External Access Config models for BlendX Core.

Defines Pydantic and SQLAlchemy models for managing External Access Integrations (EAIs)
that allow the application to connect to external APIs.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.database.models import Base


class ExternalAccessConfigCreate(BaseModel):
    """
    Pydantic model for creating an external access config record.

    Fields:
        name: Unique identifier for the EAI (e.g., "SERPER", "OPENAI").
        label: Display label for the Snowflake UI.
        description: Description of the external access purpose.
        host_ports: Comma-separated list of allowed hosts.
        enabled: Whether this EAI is enabled.
    """

    name: str = Field(..., max_length=100)
    label: str = Field(..., max_length=255)
    description: Optional[str] = None
    host_ports: str = Field(..., max_length=1000)
    enabled: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "OPENAI",
                "label": "Connection to OpenAI API",
                "description": "Access to OpenAI API for LLM capabilities",
                "host_ports": "api.openai.com",
                "enabled": True,
            }
        }
    }


class ExternalAccessConfigUpdate(BaseModel):
    """
    Pydantic model for updating an external access config record.
    """

    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    host_ports: Optional[str] = Field(None, max_length=1000)
    enabled: Optional[bool] = None


class ExternalAccessConfigResponse(BaseModel):
    """
    Pydantic model for external access config response.
    """

    id: int
    name: str
    label: str
    description: Optional[str]
    host_ports: str
    enabled: bool
    created_at: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "SERPER",
                "label": "Connection to Serper API",
                "description": "Access to Serper API for web search capabilities",
                "host_ports": "google.serper.dev",
                "enabled": True,
                "created_at": "2024-01-01T12:00:00Z",
            }
        },
    }


class ExternalAccessConfig(Base):
    """
    SQLAlchemy model for external_access_configs table.

    Stores configuration for External Access Integrations (EAIs) that can be
    dynamically created in Snowflake to allow the application to access external APIs.
    """

    __tablename__ = "external_access_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    host_ports = Column(String(1000), nullable=False)
    enabled = Column(Boolean, nullable=False, server_default="TRUE")
    created_at = Column(DateTime, server_default=func.current_timestamp())

    def __repr__(self):
        return f"<ExternalAccessConfig(name='{self.name}', host_ports='{self.host_ports}', enabled={self.enabled})>"
