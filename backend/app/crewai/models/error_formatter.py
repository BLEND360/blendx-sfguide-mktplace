"""
Error Formatter for YAML Configuration Validation

This module provides concise, human-readable error messages for YAML configuration
validation errors, focusing on identifying the specific failing section.
"""

import re
from typing import Dict, List

from app.crewai.models.tool_registry_models import ToolsRegistry


class YAMLConfigErrorFormatter:
    """Formats Pydantic validation errors into concise, actionable messages"""

    def __init__(self):
        self.tools_registry = ToolsRegistry()

    def format_validation_error(self, error_message: str) -> str:
        """
        Convert a Pydantic validation error into a concise message.

        Args:
            error_message: The raw Pydantic error message

        Returns:
            Concise error message identifying the failing section
        """
        lines = error_message.split("\n")

        if not lines:
            return "Configuration validation failed. Please check your YAML format."

        # Get the main error count
        main_error_match = re.search(r"(\d+) validation errors? for (\w+)", lines[0])
        if not main_error_match:
            return f"Configuration validation failed:\n{error_message}"

        error_count = int(main_error_match.group(1))

        # Extract failing sections
        failing_sections = self._extract_failing_sections(lines[1:])

        # Format the response
        formatted_message = f"Configuration has {error_count} validation error(s):\n\n"

        for section, errors in failing_sections.items():
            formatted_message += (
                f"**{section}**: {self._format_section_errors(section, errors)}\n\n"
            )

        # Add specific guidance based on failing sections
        formatted_message += self._get_section_guidance(failing_sections)

        # Add raw error for technical details
        formatted_message += f"\n\n**Raw Error Details:**\n```\n{error_message}\n```"

        return formatted_message

    def _extract_failing_sections(self, error_lines: List[str]) -> Dict[str, List[str]]:
        """Extract which sections are failing and their error messages"""
        sections = {}
        current_section = None
        current_error = None

        for line in error_lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a field path (starts with section name)
            if re.match(r"^\w+\.", line):
                # Save previous error if exists
                if current_section and current_error:
                    if current_section not in sections:
                        sections[current_section] = []
                    sections[current_section].append(current_error)

                # Extract section name from field path
                section_match = re.match(r"(\w+)\.", line)
                if section_match:
                    current_section = section_match.group(1)
                    current_error = self._extract_error_message(line)
            elif (
                current_error
                and line
                and not line.startswith("For further information")
            ):
                current_error += f" - {line}"

        # Add the last error
        if current_section and current_error:
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(current_error)

        # Consolidate tool errors
        for section, errors in sections.items():
            if "tools" in section and any(
                "Tool validation error" in error for error in errors
            ):
                sections[section] = [self._get_tool_format_message()]

        return sections

    def _extract_error_message(self, field_path: str) -> str:
        """Extract a human-readable error message from the field path"""
        # Handle tool-related errors
        if "tools" in field_path and any(
            tool_type in field_path
            for tool_type in [
                "CustomToolConfig",
                "SnowflakeToolConfig",
                "MCPToolConfig",
            ]
        ):
            return "Tool validation error"

        # Handle missing required fields
        if "Field required" in field_path:
            field_name = field_path.split(".")[-1]
            return f"Missing required field: {field_name}"

        # Handle other validation errors
        if "type=model_type" in field_path:
            return "Invalid format for this field"
        elif "type=missing" in field_path:
            return "Required field is missing"

        return "Invalid configuration"

    def _get_tool_format_message(self) -> str:
        """Get the standardized tool format message"""
        return (
            "Invalid tool format. Tools must be specified in one of these formats:\n"
            "  • Custom tools: 'tool_name' (e.g., 'SerperDev')\n"
            "  • Snowflake tools: {SnowflakeSearchService: [tool_names]} or {SnowflakeDataAnalyst: [tool_names]}\n"
            "  • MCP tools: {mcp: [server_names]} or {mcp: [server_names], tool_names: [specific_tools]}"
        )

    def _format_section_errors(self, section: str, errors: List[str]) -> str:
        """Format errors for a specific section"""
        if not errors:
            return "Configuration error"

        unique_errors = list(set(errors))

        # If all errors are tool validation errors, show consolidated message
        if all("Tool validation error" in error for error in unique_errors):
            return self._get_tool_format_message()

        if len(unique_errors) == 1:
            return unique_errors[0]
        else:
            return f"Multiple issues: {'; '.join(unique_errors)}"

    def _get_section_guidance(self, failing_sections: Dict[str, List[str]]) -> str:
        """Get specific guidance based on failing sections"""
        guidance = "\n**Quick Fixes:**\n"

        for section, errors in failing_sections.items():
            if section == "agents":
                guidance += "• **Agents**: Add at least one agent with role, goal, and backstory\n"
            elif section == "tasks":
                guidance += "• **Tasks**: Add at least one task with name, description, expected_output, and agent\n"
            elif section == "crews":
                guidance += (
                    "• **Crews**: Add at least one crew with name, agents, and tasks\n"
                )
            elif section == "tools":
                guidance += "• **Tools**: Use correct format:\n"
                guidance += "  - Custom tools: 'tool_name' (e.g., 'SerperDev')\n"
                guidance += (
                    "  - Snowflake tools: {SnowflakeSearchService: [tool_names]}\n"
                )
                guidance += "  - MCP tools: {mcp: [server_names]}\n"
            elif section == "flow":
                guidance += "• **Flow**: Add flow section with flow_name, class_name, and crews\n"

        guidance += "\nSee https://blend360.github.io/blendx-core/app/crewai/engine/config/README for configuration examples and documentation."
        return guidance


# Global instance for easy access
error_formatter = YAMLConfigErrorFormatter()


def format_yaml_validation_error(error_message: str) -> str:
    """
    Convenience function to format YAML validation errors.

    Args:
        error_message: The raw Pydantic validation error message

    Returns:
        Concise error message identifying the failing section
    """
    return error_formatter.format_validation_error(error_message)
