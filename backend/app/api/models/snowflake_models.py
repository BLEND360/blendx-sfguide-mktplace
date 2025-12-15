"""
Snowflake Models

Pydantic models for Snowflake search service responses and data structures.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Model for individual search result from Cortex Search Service."""

    document_id: int = Field(..., description="Unique identifier for the document")
    content: str = Field(..., description="Main content/chunk from the search result")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata fields"
    )

    model_config = {
        "json_encoders": {
            # Handle any special encoding if needed
        }
    }

    def __str__(self) -> str:
        """String representation of search result."""
        return (
            f"SearchResult(id={self.document_id}, content_length={len(self.content)})"
        )


class SearchRequest(BaseModel):
    """Model for search request parameters."""

    query: str = Field(..., description="Search query string")
    service_name: Optional[str] = Field(None, description="Cortex Search Service name")
    num_results: Optional[int] = Field(5, description="Number of results to return")
    database: Optional[str] = Field(None, description="Database name")
    schema_name: Optional[str] = Field(None, description="Schema name")
    fields: Optional[list[str]] = Field(
        default_factory=lambda: ["CHUNK"], description="Fields to retrieve"
    )
    filters: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Search filters"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "search for information about products",
                "service_name": "PRODUCT_SEARCH_SERVICE",
                "num_results": 10,
                "filters": {"category": "electronics", "brand": "ACME"},
            }
        }
    }


class SearchResponse(BaseModel):
    """Model for search response."""

    query: str = Field(..., description="Original search query")
    enhanced_query: Optional[str] = Field(
        None, description="Enhanced query with filters"
    )
    results: list[SearchResult] = Field(
        default_factory=list, description="Search results"
    )
    count: int = Field(0, description="Number of results returned")
    service_name: Optional[str] = Field(None, description="Service used for search")
    error: Optional[str] = Field(None, description="Error message if search failed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "search products",
                "enhanced_query": "search products category:electronics",
                "results": [],
                "count": 0,
                "service_name": "PRODUCT_SEARCH_SERVICE",
            }
        }
    }


class ServiceMetadata(BaseModel):
    """Model for Cortex Search Service metadata."""

    name: str = Field(..., description="Service name")
    search_column: str = Field(..., description="Primary search column")
    database: Optional[str] = Field(None, description="Database name")
    schema_name: Optional[str] = Field(None, description="Schema name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "PRODUCT_SEARCH_SERVICE",
                "search_column": "CHUNK",
                "database": "PRODUCT_DB",
                "schema_name": "CATALOG_SCHEMA",
            }
        }
    }


class SearchHealthRequest(BaseModel):
    """Model for search health test request."""

    name: str = Field(..., description="Cortex Search Service name")
    query: str = Field(..., description="Search query to test")
    database: Optional[str] = Field(
        None, description="Database name (optional, defaults to settings)"
    )
    schema_name: Optional[str] = Field(
        None, description="Schema name (optional, defaults to settings)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "PRODUCT_SEARCH_SERVICE",
                "query": "search for products",
                "database": "PRODUCT_DB",
                "schema_name": "CATALOG_SCHEMA",
            }
        }
    }


class SearchHealthResponse(BaseModel):
    """Model for search health test response."""

    service_name: str = Field(..., description="Name of the tested service")
    query: str = Field(..., description="Original search query")
    results: list[SearchResult] = Field(
        default_factory=list, description="Search results from the test"
    )
    count: int = Field(0, description="Number of results returned")
    success: bool = Field(..., description="Whether the search was successful")
    message: Optional[str] = Field(None, description="Status message or error details")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service_name": "PRODUCT_SEARCH_SERVICE",
                "query": "search for products",
                "results": [],
                "count": 0,
                "success": True,
                "message": "Search completed successfully",
            }
        }
    }
