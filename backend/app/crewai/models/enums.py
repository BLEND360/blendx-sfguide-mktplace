"""
Enums

This module contains enums used across the models.
"""

from enum import Enum


class ProcessType(str, Enum):
    """Supported crew process types"""

    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    SNOWFLAKE = "snowflake"


class MethodType(str, Enum):
    """Supported flow method types"""

    START = "start"
    LISTEN = "listen"
    ROUTER = "router"


class MethodAction(str, Enum):
    """Supported method actions"""

    RUN_CREW = "run_crew"
    CUSTOM_LOGIC = "custom_logic"


class MethodLogic(str, Enum):
    """Supported logic types for listen methods"""

    AND = "and"
    OR = "or"
