"""
YAML Configuration Validation Utilities

This module provides utilities for validating YAML configurations
to ensure they are used with the correct endpoints.
"""

from typing import Any, Dict

import yaml


def is_flow_configuration(yaml_text: str) -> bool:
    """
    Check if the YAML configuration is a flow configuration.

    Flow configurations have a 'flow' field at the root level.

    Args:
        yaml_text: YAML configuration as text

    Returns:
        True if it's a flow configuration, False otherwise
    """
    try:
        config = yaml.safe_load(yaml_text)
        if not isinstance(config, dict):
            return False
        return "flow" in config
    except yaml.YAMLError:
        # If we can't parse it, we'll let the main validation handle the error
        return False


def is_execution_group_configuration(yaml_text: str) -> bool:
    """
    Check if the YAML configuration is an execution group (crew) configuration.

    Execution group configurations do NOT have a 'flow' field at the root level.

    Args:
        yaml_text: YAML configuration as text

    Returns:
        True if it's an execution group configuration, False otherwise
    """
    try:
        config = yaml.safe_load(yaml_text)
        if not isinstance(config, dict):
            return False
        return "flow" not in config
    except yaml.YAMLError:
        # If we can't parse it, we'll let the main validation handle the error
        return False


def validate_flow_configuration(yaml_text: str) -> None:
    """
    Validate that the YAML configuration is a flow configuration.

    Args:
        yaml_text: YAML configuration as text

    Raises:
        ValueError: If the configuration is not a flow configuration
    """
    if not is_flow_configuration(yaml_text):
        raise ValueError(
            "Invalid configuration for flow endpoint. "
            "The provided YAML configuration appears to be an execution group (crew) configuration. "
            "Flow configurations must include a 'flow' field at the root level. "
            "Please use the execution group endpoints (/run-build-crews-async or /run-build-crews) instead."
        )


def validate_execution_group_configuration(yaml_text: str) -> None:
    """
    Validate that the YAML configuration is an execution group configuration.

    Args:
        yaml_text: YAML configuration as text

    Raises:
        ValueError: If the configuration is not an execution group configuration
    """
    if not is_execution_group_configuration(yaml_text):
        raise ValueError(
            "Invalid configuration for execution group endpoint. "
            "The provided YAML configuration appears to be a flow configuration. "
            "Execution group configurations should NOT include a 'flow' field at the root level. "
            "Please use the flow endpoints (/run-build-flow-async or /run-build-flow) instead."
        )
