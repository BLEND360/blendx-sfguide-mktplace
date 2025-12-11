import asyncio
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.api.models import snowflake_models
from app.config.logging_config import logger
from app.config.settings import Settings, get_settings


class SearchService:
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize Search service with settings"""
        self.settings = settings or get_settings()

    async def query_cortex_search_service(
        self,
        snowflake_service,
        query: str,
        service_name: str,
        num_chunks: int,
        db: Optional[str] = None,
        schema: Optional[str] = None,
        fields: Optional[List[str]] = None,
        connection_params: Optional[Dict[str, Any]] = None,
    ) -> List[snowflake_models.SearchResult]:
        """Query the Cortex search service and retrieve context documents asynchronously"""
        logger.info("Querying Cortex search service: %s", query)

        try:
            # Use provided parameters or fall back to BlendX Hub settings for search services
            database = (
                db
                or self.settings.blendx_hub_database
                or self.settings.snowflake_database
            )
            schema_name = (
                schema
                or self.settings.blendx_hub_schema
                or self.settings.snowflake_schema
            )
            search_fields = fields or []

            # If connection_params provided, use dynamic connection
            if connection_params:
                logger.info(f"Using dynamic connection parameters: {connection_params}")

                # Get session with dynamic parameters
                dynamic_session = snowflake_service.get_session(connection_params)

                # Create dynamic root for this session
                from snowflake.core import Root

                dynamic_root = Root(dynamic_session)

                # Get service metadata with dynamic connection
                service_meta = snowflake_service.get_service_metadata(
                    service_name, connection_params
                )
                search_column = service_meta["search_column"]

                # Get the Cortex search service using dynamic root (case-insensitive)
                # Since we don't have permissions to list services, try different case variations
                service_variations = [
                    service_name,
                    service_name.upper(),
                    service_name.lower(),
                    service_name.title(),
                ]

                cortex_search_service = None
                actual_service_name = None

                for svc_name in service_variations:
                    try:
                        cortex_search_service = (
                            dynamic_root.databases[database]
                            .schemas[schema_name]
                            .cortex_search_services[svc_name]
                        )
                        actual_service_name = svc_name
                        break
                    except Exception:
                        # Try next variation
                        continue

                if cortex_search_service is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Service '{service_name}' not found in {database}.{schema_name}. Tried variations: {service_variations}",
                    )
            else:
                # Use default connection (backward compatibility)
                logger.info("Using default connection parameters")

                # Check if we're using different database/schema than BlendX Hub defaults
                blendx_hub_db = (
                    self.settings.blendx_hub_database
                    or self.settings.snowflake_database
                )
                blendx_hub_schema = (
                    self.settings.blendx_hub_schema or self.settings.snowflake_schema
                )

                using_custom_db_schema = (
                    database != blendx_hub_db or schema_name != blendx_hub_schema
                )

                if using_custom_db_schema:
                    # For custom database/schema, create connection params for metadata loading
                    logger.info(
                        f"Using custom database/schema ({database}.{schema_name}), attempting to get metadata from service"
                    )
                    custom_connection_params = {
                        "database": database,
                        "schema": schema_name,
                    }
                    try:
                        # Try to get service metadata by querying the service directly
                        service_meta = snowflake_service.get_service_metadata(
                            service_name, custom_connection_params
                        )
                        search_column = service_meta["search_column"]
                    except Exception as e:
                        logger.warning(
                            f"Could not get service metadata: {e}, using default search column"
                        )
                        search_column = "CONTENT"  # Default search column
                else:
                    # Get service metadata for BlendX Hub database/schema
                    blendx_hub_connection_params = {
                        "database": blendx_hub_db,
                        "schema": blendx_hub_schema,
                    }
                    try:
                        service_meta = snowflake_service.get_service_metadata(
                            service_name, blendx_hub_connection_params
                        )
                        search_column = service_meta["search_column"]
                    except Exception as e:
                        logger.warning(
                            f"Could not get service metadata for BlendX Hub: {e}, using default search column"
                        )
                        search_column = "CONTENT"  # Default search column

                # Get the Cortex search service directly (case-insensitive)
                # Since we don't have permissions to list services, try different case variations
                service_variations = [
                    service_name,
                    service_name.upper(),
                    service_name.lower(),
                    service_name.title(),
                ]

                cortex_search_service = None
                actual_service_name = None

                for svc_name in service_variations:
                    try:
                        cortex_search_service = (
                            snowflake_service.root.databases[database]
                            .schemas[schema_name]
                            .cortex_search_services[svc_name]
                        )
                        actual_service_name = svc_name
                        break
                    except Exception:
                        # Try next variation
                        continue

                if cortex_search_service is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Service '{service_name}' not found in {database}.{schema_name}. Tried variations: {service_variations}",
                    )

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: cortex_search_service.search(
                    query, columns=search_fields, limit=num_chunks
                ).results,
            )

            return [
                snowflake_models.SearchResult(
                    document_id=i + 1,
                    content=r[search_column],
                    metadata={k: v for k, v in r.items() if k != search_column},
                )
                for i, r in enumerate(results)
            ]
        except Exception as e:
            logger.error("Search failed: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Global instance management - can be overridden by parameterized instances
_search_service_instance = None


def get_search_service(settings: Optional[Settings] = None) -> SearchService:
    """
    Dependency to get SearchService instance.

    Args:
        settings: Optional Settings instance. If None, uses global instance or creates new one.

    Returns:
        SearchService instance
    """
    global _search_service_instance

    # If settings provided, return new instance with those settings
    if settings is not None:
        return SearchService(settings)

    # Otherwise use global instance
    if _search_service_instance is None:
        _search_service_instance = SearchService(get_settings())
    return _search_service_instance


def create_search_service(settings: Settings) -> SearchService:
    """
    Create a new SearchService instance with specific settings.

    Args:
        settings: Settings instance to use

    Returns:
        New SearchService instance
    """
    return SearchService(settings)
