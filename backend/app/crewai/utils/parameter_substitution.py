"""
Parameter Substitution Utilities

This module provides utilities for substituting parameters in YAML configurations.
Parameters are defined as placeholders in the format {param_name} and are replaced
with their corresponding values from a parameter dictionary.
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def substitute_parameters(yaml_text: str, parameters: Optional[Dict[str, str]]) -> str:
    """
    Substitute parameters in YAML text with their corresponding values.

    Parameters are expected to be in the format {param_name} and will be replaced
    with the value from the parameters dictionary. If a parameter is not found
    in the dictionary, it will remain unchanged in the text.

    Args:
        yaml_text: The YAML configuration text containing parameter placeholders
        parameters: Dictionary mapping parameter names to their values

    Returns:
        The YAML text with parameters substituted

    Examples:
        >>> yaml_text = "description: Process {data_type} data"
        >>> parameters = {"data_type": "customer"}
        >>> substitute_parameters(yaml_text, parameters)
        'description: Process customer data'

        >>> yaml_text = "goal: Analyze {metric} for {period}"
        >>> parameters = {"metric": "sales", "period": "Q1"}
        >>> substitute_parameters(yaml_text, parameters)
        'goal: Analyze sales for Q1'
    """
    if not parameters:
        logger.debug("No parameters provided for substitution")
        return yaml_text

    # Pattern to match {param_name}
    # This will match anything inside curly braces
    pattern = r"\{([^}]+)\}"

    def replace_param(match: re.Match) -> str:
        """Replace a matched parameter with its value from the dictionary."""
        param_name = match.group(1)

        if param_name in parameters:
            value = parameters[param_name]
            logger.debug(f"Substituting parameter '{param_name}' with value '{value}'")
            return value
        else:
            # If parameter not found, leave it as is and log a warning
            logger.warning(
                f"Parameter '{param_name}' not found in parameters dictionary. "
                f"Leaving placeholder unchanged."
            )
            return match.group(0)  # Return the original {param_name}

    # Perform the substitution
    result = re.sub(pattern, replace_param, yaml_text)

    # Log summary
    if result != yaml_text:
        logger.info(
            f"Parameter substitution completed. "
            f"Substituted {len(parameters)} parameter(s)."
        )
    else:
        logger.info("No parameter substitutions were made in the YAML text.")

    return result
