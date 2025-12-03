"""
Natural Language AI Generator Module

This module provides functionality to generate AI payloads from natural language
requests using LLMs, with support for CrewAI and FlowAI configurations.
"""

import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import jsonschema
import yaml

from app.api.models.nl_ai_generator_models import MermaidChartResponse
from app.crewai.models.crew_yaml_config import CrewYAMLConfig
from app.crewai.models.error_formatter import format_yaml_validation_error
from app.crewai.models.flow_yaml_config import FlowYAMLConfig
from app.crewai.models.tool_registry_models import ToolsRegistry
from app.utils.cache_utils import TTLCache
#from app.llm_tracking_service import get_llm_tracking_service

logger = logging.getLogger(__name__)

# Cache for BlendX Hub API responses (5 minute TTL)
_tools_cache = TTLCache(ttl_seconds=300)


def _tracked_llm_call(
    llm, messages, chat_id=None, message_id=None, feature="nl_generator"
):
    """
    Simple wrapper for LLM calls. TrackedLLM handles all tracking automatically.
    This function just ensures the LLM call is made through TrackedLLM.

    Args:
        llm: The LLM instance (should be TrackedLLM)
        messages: Messages to send to the LLM
        chat_id: Optional chat ID for chat-based features
        message_id: Optional message ID for chat-based features
        feature: Feature name (default: "nl_generator")

    Returns:
        LLM response
    """
    # Simply make the LLM call - TrackedLLM will handle all tracking
    # The feature context should be set by the calling code if needed
    return llm.call(messages)


# Title extraction
def _extract_title_from_mermaid(
    mermaid_chart: Optional[str], max_len: int = 80
) -> Optional[str]:
    if not mermaid_chart or not isinstance(mermaid_chart, str):
        return None
    try:
        # Look for a line starting with 'title:' after front matter or anywhere
        for line in mermaid_chart.split("\n"):
            line_stripped = line.strip()
            if line_stripped.lower().startswith("title:"):
                title = line_stripped.split(":", 1)[1].strip()
                if title:
                    return title[:max_len]
        return None
    except Exception:
        return None


# Constants
class ConfigPaths:
    """Configuration file paths."""

    PROMPT_PATH = "app/llm/prompts/nl_ai_generator.prompt"
    CLASSIFIER_PROMPT_PATH = "app/llm/prompts/nl_ai_classifier.prompt"
    FLOW_PROMPT_PATH = "app/llm/prompts/nl_ai_generator_flow.prompt"
    CREW_PROMPT_PATH = "app/llm/prompts/nl_ai_generator_crew.prompt"
    SCHEMA_PATH = "app/llm/schemas/nl_ai_generator.schema.json"
    CLASSIFIER_SCHEMA_PATH = "app/llm/schemas/nl_ai_classifier.schema.json"
    FLOW_TEMPLATE_PATH = "app/crewai/engine/config/flow_config_template.yaml"
    CREW_TEMPLATE_PATH = "app/crewai/engine/config/crew_config_template.yaml"


class PayloadType(Enum):
    """Supported payload types."""

    CREW = "run-build-crew"
    FLOW = "run-build-flow"


class GenerationConfig:
    """Configuration for payload generation."""

    DEFAULT_MAX_TOKENS = 4000
    DEFAULT_MAX_RETRIES = 2
    REQUIRED_JSON_KEYS = {"payload", "type", "rationale"}


def _select_nl_llm_from_env(max_tokens: int):
    """Select LLM provider/model for NL generation.

    Uses Snowflake as the provider with the configured model from settings.
    """
    from app.config.settings import get_settings
    from app.handlers.lite_llm_handler import get_llm

    settings = get_settings()
    model = settings.get_nl_generator_default_model(settings.llm_model_name)

    llm = get_llm(provider="snowflake", model=model, max_tokens=max_tokens)
    return llm, model


# Custom Exceptions
class NLAIGenerationError(Exception):
    """Base exception for NL AI generation errors."""

    pass


class JSONExtractionError(NLAIGenerationError):
    """Raised when JSON cannot be extracted from LLM output."""

    pass


class PayloadValidationError(NLAIGenerationError):
    """Raised when payload validation fails."""

    pass


class FileLoadError(NLAIGenerationError):
    """Raised when file loading fails."""

    pass


def get_tools_registry_yaml() -> str:
    """
    Read and return the complete tools registry YAML content.

    Returns:
        str: Complete YAML content from the tools registry

    Raises:
        NLAIGenerationError: If tools registry YAML cannot be read
    """
    try:
        registry_path = "app/crewai/tools/tools_registry.yaml"
        return load_file_sync(registry_path)
    except Exception as e:
        raise NLAIGenerationError(f"Failed to read tools registry YAML: {e}") from e


def get_available_tools_markdown() -> str:
    """
    Generate markdown formatted list of available tools with detailed information.
    Includes tools from BlendX Hub AND static registry tools.

    Uses TTL cache (5 minutes) to avoid redundant BlendX Hub API calls.

    Returns:
        str: Markdown formatted string listing all available tools with their configurations

    Raises:
        NLAIGenerationError: If tool registry cannot be accessed
    """
    # Check cache first
    cache_key = "available_tools_markdown"
    cached_result = _tools_cache.get(cache_key)

    if cached_result is not None:
        logger.info("✅ Tools fetched from cache")
        return cached_result

    logger.info("🔄 Fetching tools from BlendX Hub (cache miss)")

    try:
        registry = ToolsRegistry()
        lines = []

        # Add header
        lines.append("**AVAILABLE TOOLS:**")
        lines.append("")

        # Add Data Analyst tools from BlendX Hub
        lines.append("**Data Analyst Tools (from BlendX Hub):**")
        _add_data_analyst_tools_from_hub(lines)
        lines.append("")

        # Add MCP tools from BlendX Hub
        lines.append("**MCP Tools (from BlendX Hub):**")
        _add_mcp_tools_from_hub(lines)
        lines.append("")

        # Add Search Services from BlendX Hub
        lines.append("**Search Services (from BlendX Hub):**")
        _add_search_services_from_hub(lines)
        lines.append("")

        # Add static registry tools
        lines.append("**CrewAI Native Tools (from Registry):**")
        crewai_tools = ["SerperDevTool", "WebsiteSearchTool"]
        for tool in crewai_tools:
            if tool in registry.available_tools:
                lines.append(f"- {tool}")
        lines.append("")

        lines.append("**Custom Tools (from Registry):**")
        custom_tools = [
            "GetStockInfo",
            "GetHistoricalData",
            "GetNews",
            "GetIncomeStatement",
            "GetBalanceSheet",
            "GetCashFlow",
        ]
        for tool in custom_tools:
            if tool in registry.available_tools:
                lines.append(f"- {tool}")
        lines.append("")

        # Add usage instructions
        lines.append(
            "**IMPORTANT: Only use tools listed above. Do not invent tool names.**"
        )

        result = "\n".join(lines)

        # Store in cache
        _tools_cache.set(cache_key, result)
        logger.info(f"💾 Tools cached for {_tools_cache.ttl_seconds}s")

        return result
    except Exception as e:
        raise NLAIGenerationError(f"Failed to get available tools: {e}") from e


def _add_specialized_tools(registry: ToolsRegistry, lines: list) -> None:
    """Add specialized tools to the lines list.

    DEPRECATED: This function is no longer used as all tools now come from BlendX Hub.
    Kept for backward compatibility but does nothing.
    """
    # All tools now come from BlendX Hub - this function is deprecated
    pass


def _add_data_analyst_tools_from_hub(lines: list) -> None:
    """Add Data Analyst tools from BlendX Hub to the lines list."""
    try:
        import httpx

        from app.config.settings import get_settings

        logger = logging.getLogger(__name__)
        settings = get_settings()

        # Get Data Analysts from BlendX Hub
        hub_url = settings.blendx_hub_url
        endpoint = f"{hub_url}/cortex-data-analyst/analysts"

        logger.info(f"Fetching Data Analysts from BlendX Hub: {endpoint}")

        with httpx.Client() as client:
            response = client.get(endpoint, timeout=30.0)
            response.raise_for_status()

            analysts = response.json()

            if not analysts:
                lines.append("- No Data Analyst tools available")
                return

            # Add Data Analyst tools with descriptions
            for analyst in analysts:
                name = analyst.get("data_analyst_name", "Unknown")
                status = analyst.get("status", "Unknown")
                stage_path = analyst.get("stage_path", "")
                tables = analyst.get("tables_referenced", [])

                # Create description based on available info
                description_parts = []
                if status:
                    description_parts.append(f"Status: {status}")
                if stage_path:
                    description_parts.append(f"Stage: {stage_path}")
                if tables:
                    description_parts.append(
                        f"Tables: {', '.join(tables[:3])}{'...' if len(tables) > 3 else ''}"
                    )

                description = (
                    " | ".join(description_parts)
                    if description_parts
                    else "Data Analyst tool from BlendX Hub"
                )

                lines.append(f"- `{name}`: {description}")

            logger.info(f"Found {len(analysts)} Data Analyst tools from BlendX Hub")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get Data Analyst tools from BlendX Hub: {str(e)}")
        lines.append("- Data Analyst tools unavailable (BlendX Hub connection failed)")


def _add_mcp_tools_from_hub(lines: list) -> None:
    """Add MCP tools from BlendX Hub to the lines list."""
    try:
        from app.services.blendx_hub_service import get_blendx_hub_service

        logger = logging.getLogger(__name__)
        blendx_service = get_blendx_hub_service()

        # Get deployments from BlendX Hub (force production to avoid LOCAL mock)
        deployments = blendx_service.get_deployments(force_production=True)

        if not deployments:
            lines.append("- No MCP servers available")
            return

        mcp_servers = []

        for deployment in deployments:
            server_name = deployment.service_name

            # Tools are now included directly in the deployment response
            tools_data = getattr(deployment, "tools", None)

            if tools_data:
                try:
                    # Parse the tools - can be either JSON string or list
                    import json

                    if isinstance(tools_data, str):
                        tools_list = json.loads(tools_data)
                    elif isinstance(tools_data, list):
                        tools_list = tools_data
                    else:
                        tools_list = []

                    tool_entries = []
                    for tool in tools_list:
                        if isinstance(tool, dict):
                            name = tool.get("name", "Unknown")
                            description = tool.get("description", "")

                            # Extract description up to the first section divider (Args, Returns, Note, Example, etc.)
                            if description:
                                desc_lines = description.strip().split("\n")
                                summary_lines = []

                                for desc_line in desc_lines:
                                    cleaned = desc_line.strip()

                                    # Stop at section dividers
                                    if cleaned and any(
                                        cleaned.startswith(section)
                                        for section in [
                                            "Args:",
                                            "Returns:",
                                            "Note:",
                                            "Example:",
                                            "Raises:",
                                            "Yields:",
                                            "See Also:",
                                            "Warnings:",
                                            "Dependencies:",
                                        ]
                                    ):
                                        break

                                    # Add non-empty lines that are part of the description
                                    if cleaned:
                                        summary_lines.append(cleaned)

                                # Join the summary lines
                                if summary_lines:
                                    description = " ".join(summary_lines)

                                    # Remove trailing period for consistency
                                    if description.endswith("."):
                                        description = description[:-1]
                                else:
                                    description = ""

                            tool_entries.append(
                                {"name": name, "description": description}
                            )
                        elif isinstance(tool, str):
                            tool_entries.append({"name": tool, "description": ""})

                    if tool_entries:
                        mcp_servers.append(
                            {"server_name": server_name, "tools": tool_entries}
                        )
                        tool_names = [t["name"] for t in tool_entries]
                        logger.info(
                            f"Found {len(tool_names)} tools in MCP server '{server_name}': {tool_names}"
                        )

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse tools JSON for server '{server_name}': {str(e)}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Error processing tools for server '{server_name}': {str(e)}"
                    )
            else:
                logger.debug(f"No tools found in deployment for server '{server_name}'")

        # Add MCP servers to the lines with better formatting
        if mcp_servers:
            for server_info in mcp_servers:
                server_name = server_info["server_name"]
                tools = server_info["tools"]

                # Add server name with clear structure
                lines.append(f"- **MCP Server Name:** `{server_name}`")

                # Extract tool names for easy reference
                tool_names = [
                    t.get("name", t) if isinstance(t, dict) else t for t in tools
                ]
                lines.append(f"  - **Available tool_names:** {tool_names}")

                # Add descriptions for understanding
                lines.append(f"  - **Tool descriptions:**")
                for tool in tools:
                    if isinstance(tool, dict):
                        name = tool.get("name", "Unknown")
                        desc = tool.get("description", "")
                        if desc:
                            lines.append(f"    - `{name}`: {desc}")
                        else:
                            lines.append(f"    - `{name}`: No description available")
                    else:
                        lines.append(f"    - `{tool}`: No description available")
        else:
            lines.append("- No MCP tools available")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get MCP tools from BlendX Hub: {str(e)}")
        lines.append("- MCP tools unavailable (BlendX Hub connection failed)")


def _add_search_services_from_hub(lines: list) -> None:
    """Add available Search Services from BlendX Hub to the lines list."""
    try:
        from app.services.blendx_hub_search_service import (
            get_blendx_hub_search_service,
        )

        logger = logging.getLogger(__name__)
        hub_service = get_blendx_hub_search_service()

        services = hub_service.get_available_search_services()

        if not services:
            lines.append("- No search services available")
            return

        # Add detailed information for each service
        for svc in services:
            name = svc.get("service_name") or svc.get("name") or "Unknown"
            status = svc.get("status", "Unknown")
            description = svc.get("description", "")

            # Create description based on available info
            description_parts = []
            if status:
                description_parts.append(f"Status: {status}")
            if description:
                description_parts.append(f"Description: {description}")

            service_desc = (
                " | ".join(description_parts)
                if description_parts
                else "Search service from BlendX Hub"
            )

            lines.append(f"- `{name}`: {service_desc}")

        logger.info(f"Found {len(services)} search services from BlendX Hub")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get Search Services from BlendX Hub: {str(e)}")
        lines.append("- Search services unavailable (BlendX Hub connection failed)")


def prepare_nl_ai_prompt(
    user_request: str,
    prompt_template: str,
    tools_md: str,
    config_template_flow: str = "",
    config_template_crew: str = "",
    error_feedback: str = "",
    previous_workflow_yaml: str = "",
    chat_history: str = "",
    workflow_type: str = None,
) -> str:
    """
    Prepare the natural language AI prompt with all necessary substitutions.

    Args:
        user_request: The user's natural language request
        prompt_template: The base prompt template
        tools_md: Markdown string with available tools (pre-fetched to avoid redundant calls)
        config_template_flow: Flow configuration template
        config_template_crew: Crew configuration template
        error_feedback: Error feedback from previous attempts
        previous_workflow_yaml: YAML text of the previous workflow (for refinement)
        chat_history: Previous chat messages for context
        workflow_type: Type of workflow (flow or crew) for specialized prompts

    Returns:
        str: The prepared prompt string

    Raises:
        NLAIGenerationError: If prompt preparation fails
    """
    if not user_request or not prompt_template or not tools_md:
        raise ValueError("user_request, prompt_template, and tools_md cannot be empty")

    try:
        # If workflow_type is specified, only include the relevant template
        if workflow_type == PayloadType.FLOW.value:
            # Only include flow template
            substitutions = {
                "{{available_tools}}": tools_md,
                "{{user_request}}": user_request,
                "{{flow_config_template}}": config_template_flow,
                "{{error_feedback}}": error_feedback,
                "{{previous_workflow_yaml}}": previous_workflow_yaml,
                "{{chat_history}}": chat_history,
            }
        elif workflow_type == PayloadType.CREW.value:
            # Only include crew template
            substitutions = {
                "{{available_tools}}": tools_md,
                "{{user_request}}": user_request,
                "{{crew_config_template}}": config_template_crew,
                "{{error_feedback}}": error_feedback,
                "{{previous_workflow_yaml}}": previous_workflow_yaml,
                "{{chat_history}}": chat_history,
            }
        else:
            # Legacy behavior: include both templates
            substitutions = {
                "{{available_tools}}": tools_md,
                "{{user_request}}": user_request,
                "{{flow_config_template}}": config_template_flow,
                "{{crew_config_template}}": config_template_crew,
                "{{error_feedback}}": error_feedback,
                "{{previous_workflow_yaml}}": previous_workflow_yaml,
                "{{chat_history}}": chat_history,
            }

        prompt = prompt_template
        for placeholder, value in substitutions.items():
            prompt = prompt.replace(placeholder, value)

        return prompt
    except Exception as e:
        raise NLAIGenerationError(f"Failed to prepare prompt: {e}") from e


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON object from text, handling markdown code blocks.

    Args:
        text: Text containing JSON object

    Returns:
        str: Extracted JSON string

    Raises:
        JSONExtractionError: If no valid JSON object is found
    """
    if not text:
        raise JSONExtractionError("Input text is empty")

    # Remove markdown code blocks
    cleaned_text = re.sub(r"```[a-zA-Z]*", "", text)
    cleaned_text = cleaned_text.replace("```", "")

    # Find JSON object
    json_match = re.search(r"\{[\s\S]*\}", cleaned_text)
    if not json_match:
        raise JSONExtractionError("No JSON object found in LLM output")

    return json_match.group(0)


def _fix_json_string_escaping(json_str: str) -> str:
    """
    Fix common JSON escaping issues in LLM-generated JSON strings.

    LLMs often produce JSON with:
    - Unescaped newlines inside string values
    - Unescaped quotes inside string values
    - Unescaped backslashes

    Args:
        json_str: Raw JSON string from LLM

    Returns:
        str: JSON string with fixed escaping
    """
    # Strategy: Find string values and fix escaping within them
    result = []
    i = 0
    in_string = False
    string_start = -1

    while i < len(json_str):
        char = json_str[i]

        if char == '"' and (i == 0 or json_str[i-1] != '\\'):
            if not in_string:
                # Starting a string
                in_string = True
                string_start = i
                result.append(char)
            else:
                # Ending a string
                in_string = False
                result.append(char)
        elif in_string:
            # Inside a string - fix unescaped characters
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            else:
                result.append(char)
        else:
            result.append(char)

        i += 1

    return ''.join(result)


def _generate_mermaid_chart_with_structured_output(
    user_request: str,
    yaml_config: str,
    config_template_flow: str,
    config_template_crew: str,
) -> Optional[str]:
    """
    Generate mermaid chart using LLM with structured output.

    Uses Pydantic model for structured output to ensure valid JSON response
    and avoid parsing errors from malformed LLM output.

    Args:
        user_request: The user's original request
        yaml_config: The generated YAML configuration
        config_template_flow: Flow configuration template
        config_template_crew: Crew configuration template

    Returns:
        str: Valid mermaid chart code, or None if generation fails
    """
    try:
        from app.handlers.lite_llm_handler import get_snowflake_litellm_service
        from app.config.settings import get_settings

        settings = get_settings()

        # Load the mermaid prompt template
        mermaid_prompt = load_file_sync(
            "app/llm/prompts/nl_ai_mermaid_generator.prompt"
        )

        # Prepare the prompt
        mermaid_input = mermaid_prompt
        mermaid_input = mermaid_input.replace("{{user_request}}", user_request)
        mermaid_input = mermaid_input.replace("{{yaml_config}}", yaml_config)
        mermaid_input = mermaid_input.replace(
            "{{flow_config_template}}", config_template_flow
        )
        mermaid_input = mermaid_input.replace(
            "{{crew_config_template}}", config_template_crew
        )
        mermaid_input = mermaid_input.replace("{{error_feedback}}", "")

        # Build base URL for native Snowflake endpoint (supports response_format)
        host = settings.snowflake_host
        base_url = f"https://{host}/api/v2/cortex/inference:complete"

        # Get private key for JWT auth
        private_key = None
        if settings.snowflake_private_key_path:
            try:
                with open(settings.snowflake_private_key_path, "r") as f:
                    private_key = f.read()
            except Exception as e:
                logger.warning(f"Could not load private key: {e}")

        # Use SnowflakeLitellmService with response_format for structured output
        mermaid_llm = get_snowflake_litellm_service(
            base_url=base_url,
            snowflake_account=settings.snowflake_account,
            snowflake_service_user=settings.snowflake_service_user or settings.snowflake_user,
            snowflake_authmethod="jwt" if private_key else "oauth",
            api_key=private_key,
            temperature=0.1,
            max_tokens=GenerationConfig.DEFAULT_MAX_TOKENS,
            response_format=MermaidChartResponse.model_json_schema(),
        )

        # Call LLM with structured output
        mermaid_response = mermaid_llm.completion(
            model="claude-3-5-sonnet",
            messages=[{"role": "user", "content": mermaid_input}],
            timeout=120,
        )

        # Parse the structured response
        response_content = mermaid_response.choices[0].message.content
        response_data = json.loads(response_content)
        mermaid_chart_raw = response_data.get("mermaid_chart")

        if mermaid_chart_raw:
            # Clean up any markdown code fences if present
            mermaid_chart = (
                mermaid_chart_raw
                .replace("```mermaid", "")
                .replace("```", "")
                .strip()
            )
            logger.info("✅ Mermaid chart generated successfully with structured output")
            return mermaid_chart
        else:
            logger.warning("Mermaid chart response did not contain 'mermaid_chart' key")
            return None

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse mermaid chart JSON response: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to generate mermaid chart: {e}")
        return None


def load_file_sync(path: str) -> str:
    """
    Synchronously load file content with proper error handling.

    Args:
        path: File path to load

    Returns:
        str: File content

    Raises:
        FileLoadError: If file cannot be loaded
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            raise FileLoadError(f"File not found: {path}")

        with file_path.open("r", encoding="utf-8") as f:
            return f.read()
    except (OSError, IOError) as e:
        raise FileLoadError(f"Failed to load file {path}: {e}") from e


def validate_payload_by_type(yaml_dict: dict, type_: str) -> Tuple[bool, Optional[str]]:
    """
    Validate payload based on its type.

    Args:
        yaml_dict: YAML dictionary to validate
        type_: Payload type identifier

    Returns:
        Tuple of (is_valid, error_message)

    Raises:
        ValueError: If type is unknown
    """
    if not yaml_dict:
        return False, "YAML dictionary is empty"

    try:
        if type_ == PayloadType.CREW.value:
            CrewYAMLConfig(**yaml_dict)
        elif type_ == PayloadType.FLOW.value:
            FlowYAMLConfig(**yaml_dict)
        else:
            raise ValueError(f"Unknown payload type: {type_}")
        return True, None
    except Exception as e:
        return False, str(e)


def _validate_json_structure(result: dict) -> Optional[str]:
    """
    Validate that JSON has required top-level keys.

    Args:
        result: Parsed JSON dictionary

    Returns:
        Error message if validation fails, None if successful
    """
    missing_keys = GenerationConfig.REQUIRED_JSON_KEYS - result.keys()
    if missing_keys:
        return (
            f"Missing required top-level key(s): {', '.join(missing_keys)}. "
            "You must include all three: 'payload', 'type', and 'rationale' "
            "at the top level of your JSON response."
        )
    return None


def _build_error_feedback(
    last_llm_output: str,
    last_payload: Optional[dict],
    last_payload_validation_error: str,
    last_error: Optional[str],
    missing_keys_feedback: str,
) -> str:
    """Build comprehensive error feedback string."""
    feedback_parts = []

    if last_llm_output:
        feedback_parts.append(f"Previous LLM output (JSON):\n{last_llm_output}")
    if last_payload:
        feedback_parts.append(
            f"Previous payload object:\n{json.dumps(last_payload, indent=2)}"
        )
    if last_payload_validation_error:
        feedback_parts.append(
            f"Payload validation error:\n{last_payload_validation_error}"
        )
    if last_error and not last_payload_validation_error:
        feedback_parts.append(f"Other error:\n{last_error}")
    if missing_keys_feedback:
        feedback_parts.append(missing_keys_feedback)

    return "\n\n".join(feedback_parts)


def _process_llm_response(
    response_str: str, schema: dict
) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
    """
    Process LLM response and extract validated JSON.

    Returns:
        Tuple of (result_dict, missing_keys_feedback, error_message)
    """
    try:
        logger.info("🔄 Extracting JSON from LLM response...")
        json_str = extract_json_from_text(response_str)
        logger.info(f"✅ JSON extracted successfully, length: {len(json_str)}")

        logger.info("🔄 Parsing JSON...")
        result = json.loads(json_str)
        logger.info(f"✅ JSON parsed successfully, keys: {list(result.keys())}")

        # Validate JSON structure
        logger.info("🔄 Validating JSON structure...")
        missing_keys_error = _validate_json_structure(result)
        if missing_keys_error:
            logger.error(f"❌ JSON structure validation failed: {missing_keys_error}")
            return None, missing_keys_error, missing_keys_error

        # Validate against schema
        logger.info("🔄 Validating against schema...")
        jsonschema.validate(instance=result, schema=schema)
        logger.info("✅ Schema validation successful")
        return result, None, None

    except JSONExtractionError as e:
        logger.error(f"❌ JSON extraction error: {e}")
        logger.error(f"Response preview: {response_str[:500]}...")
        return None, None, f"JSON extraction error: {e}"
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {e}")
        logger.error(
            f"JSON string preview: {json_str[:500] if 'json_str' in locals() else 'N/A'}..."
        )
        return None, None, f"JSON parsing error: {e}"
    except jsonschema.ValidationError as e:
        logger.error(f"❌ Schema validation error: {e}")
        return None, None, f"Schema validation error: {e}"
    except Exception as e:
        logger.error(f"❌ LLM output processing error: {e}", exc_info=True)
        return None, None, f"LLM output processing error: {e}"


def _process_yaml_payload(payload: dict, type_: str) -> Tuple[bool, str]:
    """
    Process and validate YAML payload.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        logger.info(f"🔄 Parsing YAML from payload (type: {type_})...")
        yaml_text = payload.get("yaml_text", "")
        if not yaml_text:
            logger.error("❌ No yaml_text found in payload")
            return False, "No yaml_text found in payload"

        logger.info(f"📄 YAML text length: {len(yaml_text)}")
        yaml_dict = yaml.safe_load(yaml_text)
        logger.info(
            f"✅ YAML parsed successfully, top-level keys: {list(yaml_dict.keys()) if isinstance(yaml_dict, dict) else 'N/A'}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to parse YAML: {e}", exc_info=True)
        return False, f"Failed to parse YAML: {e}"

    logger.info(f"🔄 Validating payload by type: {type_}")
    is_valid, error = validate_payload_by_type(yaml_dict, type_)
    if not is_valid:
        logger.error(f"❌ Payload validation failed: {error}")
        formatted_error = format_yaml_validation_error(error)
        logger.error(f"❌ Formatted error: {formatted_error}")
        return False, formatted_error

    logger.info("✅ YAML payload validation successful")
    return True, ""


def generate_nl_ai_payload_with_context(
    user_request: str,
    chat_id: str,
    message_id: Optional[str] = None,
    max_tokens: int = GenerationConfig.DEFAULT_MAX_TOKENS,
    max_retries: int = GenerationConfig.DEFAULT_MAX_RETRIES,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Generate AI payload from natural language request with chat context and previous workflow.

    Args:
        user_request: Natural language description of desired AI workflow
        chat_id: Chat session identifier for context retrieval
        max_tokens: Maximum tokens for LLM response
        max_retries: Maximum number of retry attempts

    Returns:
        Tuple of (generated_payload, error_message)
    """
    from app.database.db import get_new_db_session
    from app.database.repositories.chat_messages_repository import (
        ChatMessagesRepository,
    )
    from app.database.repositories.workflows_repository import WorkflowsRepository

    if not user_request or not user_request.strip():
        raise ValueError("user_request cannot be empty")

    if max_tokens <= 0 or max_retries < 0:
        raise ValueError(
            "max_tokens must be positive and max_retries must be non-negative"
        )

    try:
        # Get context from database in a single optimized query
        previous_workflow_yaml = ""
        conversation_summary = ""

        with get_new_db_session() as db:
            workflow_repo = WorkflowsRepository(db)
            previous_workflow, conversation_summary = (
                workflow_repo.get_chat_context_for_generation(chat_id)
            )

            if previous_workflow:
                previous_workflow_yaml = previous_workflow.yaml_text or ""

            if not conversation_summary:
                conversation_summary = ""

        # OPTIMIZATION: Run classification and tools fetching in parallel
        import concurrent.futures

        previous_workflow_type = ""
        if previous_workflow:
            previous_workflow_type = getattr(previous_workflow, "type", "")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks in parallel
            logger.info("🔍 Starting classification (parallel)")
            classification_future = executor.submit(
                classify_workflow_type,
                user_request,
                conversation_summary,
                previous_workflow_type,
            )

            logger.info("🔧 Starting tools fetch (parallel)")
            tools_future = executor.submit(get_available_tools_markdown)

            # Wait for both to complete
            workflow_type, classification_reasoning, confidence = (
                classification_future.result()
            )
            logger.info(
                f"✅ Classification complete: {workflow_type} (confidence: {confidence})"
            )

            tools_md = tools_future.result()
            logger.info(f"✅ Tools fetched ({len(tools_md)} characters)")

        # Load configuration files for the specific type
        config_files = _load_configuration_files(workflow_type)
        schema = json.loads(config_files["schema"])

        # Get LLM for NL generation
        llm, model_used = _select_nl_llm_from_env(max_tokens)

        # Initialize tracking variables
        state = _initialize_generation_state()

        for attempt in range(max_retries + 1):
            try:
                # Build error feedback
                error_feedback = _build_error_feedback(
                    state["last_llm_output"],
                    state["last_payload"],
                    state["last_payload_validation_error"],
                    state["last_error"],
                    state["missing_keys_feedback"],
                )

                # Prepare and call LLM with context and workflow type
                llm_input = prepare_nl_ai_prompt(
                    user_request=user_request,
                    prompt_template=config_files["prompt_template"],
                    tools_md=tools_md,
                    config_template_flow=config_files["config_template_flow"],
                    config_template_crew=config_files["config_template_crew"],
                    error_feedback=error_feedback,
                    previous_workflow_yaml=previous_workflow_yaml,
                    chat_history=conversation_summary,
                    workflow_type=workflow_type,
                )

                response_str = _tracked_llm_call(
                    llm,
                    messages=[{"role": "user", "content": llm_input}],
                    chat_id=chat_id,
                    message_id=message_id,
                    feature="nl_generator",
                )
                state["last_llm_output"] = response_str
                state["missing_keys_feedback"] = ""

                # Process LLM response
                result, missing_keys_feedback, error = _process_llm_response(
                    response_str, schema
                )
                if error:
                    state["last_error"] = error
                    state["missing_keys_feedback"] = missing_keys_feedback or ""
                    continue

                # Extract components
                payload = result["payload"]
                type_ = result["type"]
                rationale = result["rationale"]
                state["last_payload"] = payload
                state["last_payload_validation_error"] = ""

                # Log the generated YAML for debugging
                yaml_text = payload.get("yaml_text", "")
                if yaml_text:
                    logger.info("=== GENERATED YAML (SYNC) ===")
                    logger.info(yaml_text)
                    logger.info("=== END GENERATED YAML (SYNC) ===")
                else:
                    logger.warning("No YAML text found in generated payload (SYNC)")

                # Validate YAML payload
                is_valid, yaml_error = _process_yaml_payload(payload, type_)
                if not is_valid:
                    logger.error(f"YAML validation failed: {yaml_error}")
                    state["last_payload_validation_error"] = yaml_error
                    continue

                # Generate mermaid chart using LLM with structured output
                mermaid_chart = ""
                if payload.get("yaml_text"):
                    mermaid_chart = _generate_mermaid_chart_with_structured_output(
                        user_request=user_request,
                        yaml_config=payload["yaml_text"],
                        config_template_flow=config_files["config_template_flow"],
                        config_template_crew=config_files["config_template_crew"],
                    ) or ""

                # Success - return the result with classification info
                title_generated = _extract_title_from_mermaid(mermaid_chart)
                result = {
                    "payload": payload,
                    "type": type_,
                    "rationale": rationale,
                    "mermaid_chart": mermaid_chart,
                    "title": title_generated,
                    "model": model_used,
                }

                # Add classification info
                if classification_reasoning:
                    result["classification_reasoning"] = classification_reasoning
                if confidence:
                    result["classification_confidence"] = confidence

                return result, None

            except Exception as e:
                state["last_error"] = str(e)
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    raise NLAIGenerationError(
                        f"All retry attempts failed. Last error: {e}"
                    ) from e

        # This should never be reached due to the raise above, but just in case
        raise NLAIGenerationError("Generation failed after all retry attempts")

    except Exception as e:
        logger.error(f"Critical error in generate_nl_ai_payload_with_context: {e}")
        return {}, str(e)


def generate_nl_ai_payload(
    user_request: str,
    max_tokens: int = GenerationConfig.DEFAULT_MAX_TOKENS,
    max_retries: int = GenerationConfig.DEFAULT_MAX_RETRIES,
    enable_classification: bool = True,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Generate AI payload from natural language request.

    Uses a two-phase approach by default:
    1. Classify whether the request requires a Flow or Crew
    2. Generate using only the relevant prompt and template

    Args:
        user_request: Natural language description of desired AI workflow
        max_tokens: Maximum tokens for LLM response
        max_retries: Maximum number of retry attempts
        enable_classification: Use pre-classification (default: True, set False for legacy behavior)

    Returns:
        Tuple of (generated_payload, error_message)

    Raises:
        NLAIGenerationError: If critical errors occur during generation
        ValueError: If input parameters are invalid
    """
    if not user_request or not user_request.strip():
        raise ValueError("user_request cannot be empty")

    if max_tokens <= 0 or max_retries < 0:
        raise ValueError(
            "max_tokens must be positive and max_retries must be non-negative"
        )

    try:
        logger.info(f"Starting NL generation with max_retries={max_retries}")

        # OPTIMIZATION: Run classification and tools fetching in parallel
        # This saves ~10 seconds by executing both operations concurrently
        import concurrent.futures

        workflow_type = None
        classification_reasoning = None
        confidence = None
        tools_md = ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks in parallel
            classification_future = None
            if enable_classification:
                logger.info("🔍 Starting classification (parallel)")
                classification_future = executor.submit(
                    classify_workflow_type,
                    user_request,
                    "",  # chat_history
                    "",  # previous_workflow_type
                )

            logger.info("🔧 Starting tools fetch (parallel)")
            tools_future = executor.submit(get_available_tools_markdown)

            # Wait for both to complete
            if classification_future:
                workflow_type, classification_reasoning, confidence = (
                    classification_future.result()
                )
                logger.info(
                    f"✅ Classification complete: {workflow_type} (confidence: {confidence})"
                )

            tools_md = tools_future.result()
            logger.info(f"✅ Tools fetched ({len(tools_md)} characters)")

        # Load configuration files (will load specific prompt if workflow_type is set)
        config_files = _load_configuration_files(workflow_type)
        schema = json.loads(config_files["schema"])

        # Get LLM for NL generation
        llm, model_used = _select_nl_llm_from_env(max_tokens)

        # Initialize tracking variables
        state = _initialize_generation_state()

        # Retry loop
        for attempt in range(max_retries + 1):
            logger.info(f"NL generation attempt {attempt + 1}/{max_retries + 1}")
            try:
                # Build error feedback
                error_feedback = _build_error_feedback(
                    state["last_llm_output"],
                    state["last_payload"],
                    state["last_payload_validation_error"],
                    state["last_error"],
                    state["missing_keys_feedback"],
                )

                # Prepare and call LLM (with workflow_type if using classification)
                llm_input = prepare_nl_ai_prompt(
                    user_request=user_request,
                    prompt_template=config_files["prompt_template"],
                    tools_md=tools_md,
                    config_template_flow=config_files["config_template_flow"],
                    config_template_crew=config_files["config_template_crew"],
                    error_feedback=error_feedback,
                    previous_workflow_yaml="",
                    chat_history="",
                    workflow_type=workflow_type,
                )

                response_str = _tracked_llm_call(
                    llm,
                    messages=[{"role": "user", "content": llm_input}],
                    chat_id=None,  # No chat context for this function
                    message_id=None,
                    feature="nl_generator",
                )
                state["last_llm_output"] = response_str
                state["missing_keys_feedback"] = ""

                logger.info(
                    f"📥 Received LLM response for attempt {attempt + 1}, processing..."
                )

                # Process LLM response
                result, missing_keys_feedback, error = _process_llm_response(
                    response_str, schema
                )
                if error:
                    logger.error(
                        f"❌ LLM response processing failed for attempt {attempt + 1}: {error}"
                    )
                    state["last_error"] = error
                    state["missing_keys_feedback"] = missing_keys_feedback or ""
                    continue

                logger.info(
                    f"✅ LLM response processed successfully for attempt {attempt + 1}"
                )

                # Extract components
                payload = result["payload"]
                type_ = result["type"]
                rationale = result["rationale"]
                state["last_payload"] = payload
                state["last_payload_validation_error"] = ""

                logger.info(
                    f"📋 Extracted payload components - type: {type_}, rationale length: {len(rationale) if rationale else 0}"
                )

                # Validate YAML payload
                logger.info(f"🔍 Validating YAML payload for attempt {attempt + 1}")
                is_valid, validation_error = _process_yaml_payload(payload, type_)
                if is_valid:
                    logger.info(f"YAML validation successful for attempt {attempt + 1}")
                    # Generate mermaid chart using LLM with structured output
                    mermaid_chart = _generate_mermaid_chart_with_structured_output(
                        user_request=user_request,
                        yaml_config=payload["yaml_text"],
                        config_template_flow=config_files["config_template_flow"],
                        config_template_crew=config_files["config_template_crew"],
                    )
                    title_generated = _extract_title_from_mermaid(mermaid_chart)

                    result = {
                        "payload": payload,
                        "type": type_,
                        "rationale": rationale,
                        "mermaid_chart": mermaid_chart,
                        "title": title_generated,
                        "model": model_used,
                    }

                    # Add classification info if available
                    if classification_reasoning:
                        result["classification_reasoning"] = classification_reasoning
                    if confidence:
                        result["classification_confidence"] = confidence

                    return result, None
                else:
                    logger.error(
                        f"❌ YAML validation failed for attempt {attempt + 1}: {validation_error}"
                    )
                    state["last_payload_validation_error"] = validation_error
                    state["last_error"] = f"YAML validation failed: {validation_error}"

            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {e}"
                state["last_error"] = error_msg
                logger.error(
                    f"💥 Generation attempt {attempt + 1} failed with exception: {e}",
                    exc_info=True,
                )

        logger.error(
            f"All {max_retries + 1} attempts failed. Last error: {state['last_error']}"
        )
        logger.error(
            f"Last payload validation error: {state['last_payload_validation_error']}"
        )
        logger.error(f"Last LLM output: {state['last_llm_output'][:500]}...")

        return (
            {},
            f"Failed to generate valid payload after {max_retries + 1} attempts. Last error: {state['last_error']}",
        )

    except Exception as e:
        raise NLAIGenerationError(f"Critical error in payload generation: {e}") from e


def _load_configuration_files(workflow_type: str = None) -> Dict[str, str]:
    """
    Load required configuration files.

    Args:
        workflow_type: If specified, loads only the prompt for that type.
                      Otherwise loads the legacy unified prompt.

    Returns:
        Dictionary with loaded configuration files
    """
    try:
        config = {
            "schema": load_file_sync(ConfigPaths.SCHEMA_PATH),
            "config_template_flow": load_file_sync(ConfigPaths.FLOW_TEMPLATE_PATH),
            "config_template_crew": load_file_sync(ConfigPaths.CREW_TEMPLATE_PATH),
        }

        # Load the appropriate prompt based on workflow type
        if workflow_type == PayloadType.FLOW.value:
            config["prompt_template"] = load_file_sync(ConfigPaths.FLOW_PROMPT_PATH)
        elif workflow_type == PayloadType.CREW.value:
            config["prompt_template"] = load_file_sync(ConfigPaths.CREW_PROMPT_PATH)
        else:
            # Legacy: load unified prompt
            config["prompt_template"] = load_file_sync(ConfigPaths.PROMPT_PATH)

        return config
    except FileLoadError as e:
        raise NLAIGenerationError(f"Failed to load configuration files: {e}") from e


def _initialize_generation_state() -> Dict[str, Any]:
    """Initialize state variables for generation tracking."""
    return {
        "last_llm_output": "",
        "last_payload": None,
        "last_payload_validation_error": "",
        "missing_keys_feedback": "",
        "last_error": None,
    }


def classify_workflow_type(
    user_request: str,
    chat_history: str = "",
    previous_workflow_type: str = "",
    max_tokens: int = 500,
) -> Tuple[str, str, str]:
    """
    Classify whether the user request requires a Flow or Crew.

    Args:
        user_request: The user's natural language request
        chat_history: Previous conversation context
        previous_workflow_type: Type of previous workflow if refining
        max_tokens: Maximum tokens for LLM response

    Returns:
        Tuple of (workflow_type, reasoning, confidence)
        - workflow_type: "run-build-flow" or "run-build-crew"
        - reasoning: Explanation of the classification
        - confidence: "high", "medium", or "low"

    Raises:
        NLAIGenerationError: If classification fails
    """
    try:
        logger.info("🔍 Classifying workflow type...")

        # Load classifier prompt and schema
        classifier_prompt_template = load_file_sync(ConfigPaths.CLASSIFIER_PROMPT_PATH)
        classifier_schema = json.loads(
            load_file_sync(ConfigPaths.CLASSIFIER_SCHEMA_PATH)
        )

        # Prepare classifier prompt
        substitutions = {
            "{{user_request}}": user_request,
            "{{chat_history}}": chat_history or "None",
            "{{previous_workflow_type}}": previous_workflow_type or "None",
        }

        classifier_prompt = classifier_prompt_template
        for placeholder, value in substitutions.items():
            classifier_prompt = classifier_prompt.replace(placeholder, value)

        from app.handlers.lite_llm_handler import get_llm

        llm = get_llm(provider="snowflake", model="claude-3-5-sonnet", max_tokens=max_tokens)

        # Call LLM
        response_str = llm.call(
            messages=[{"role": "user", "content": classifier_prompt}]
        )

        # Parse response
        json_str = extract_json_from_text(response_str)
        result = json.loads(json_str)

        # Validate against schema
        jsonschema.validate(instance=result, schema=classifier_schema)

        workflow_type = result["type"]
        reasoning = result["reasoning"]
        confidence = result["confidence"]

        logger.info(
            f"✅ Classification complete: {workflow_type} (confidence: {confidence})"
        )
        logger.info(f"💡 Reasoning: {reasoning}")

        return workflow_type, reasoning, confidence

    except Exception as e:
        logger.error(f"❌ Classification failed: {e}", exc_info=True)
        # Default to Flow if classification fails (more versatile)
        logger.warning("⚠️  Defaulting to Flow due to classification failure")
        return (
            PayloadType.FLOW.value,
            "Defaulted to Flow due to classification error",
            "low",
        )
