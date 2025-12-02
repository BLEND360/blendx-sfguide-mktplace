"""
Method Models

This module contains Pydantic models for validating flow method configurations
used in flow engine.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, RootModel, model_validator

from app.crewai.models.enums import MethodAction, MethodLogic, MethodType


class InitializeStateConfig(RootModel):
    """Configuration for initializing state in start methods"""

    # Dynamic field names with string values
    # This allows any key-value pairs for state initialization
    root: Dict[str, str] = Field(
        ..., description="State initialization key-value pairs"
    )


class UpdateStateConfig(RootModel):
    """Configuration for updating state in methods"""

    # Dynamic field names with any values
    # This allows any key-value pairs for state updates
    root: Dict[str, Any] = Field(..., description="State update key-value pairs")


class RouteConfig(BaseModel):
    """Configuration for router method routes"""

    true: Optional[str] = Field(None, description="Route when condition is true")
    false: Optional[str] = Field(None, description="Route when condition is false")
    default: Optional[str] = Field(None, description="Default route")


class FlowMethodConfig(BaseModel):
    """Configuration for a flow method"""

    name: str = Field(..., description="Name of the flow method")
    type: MethodType = Field(..., description="Type of the flow method")

    # Optional fields based on method type
    action: Optional[MethodAction] = Field(None, description="Action to perform")
    crew: Optional[str] = Field(None, description="Crew name to run")
    output: Optional[str] = Field(None, description="Output message")

    # Listen method specific fields
    listen_to: Optional[List[str]] = Field(
        None, description="List of methods to listen to"
    )
    logic: Optional[MethodLogic] = Field(
        None, description="Logic type for multiple listen targets"
    )

    # Router method specific fields
    condition: Optional[str] = Field(None, description="Condition for routing")
    routes: Optional[RouteConfig] = Field(None, description="Route configuration")

    # State management fields
    initialize_state: Optional[InitializeStateConfig] = Field(
        None, description="State initialization"
    )
    update_state: Optional[UpdateStateConfig] = Field(None, description="State updates")

    # Custom logic field
    custom_logic: Optional[Dict[str, Any]] = Field(
        None, description="Custom logic configuration"
    )

    @model_validator(mode="after")
    def validate_method_configuration(self):
        """Validate method configuration based on type"""

        if self.type == MethodType.START:
            # Start methods can have initialize_state and action
            if self.action and self.action != MethodAction.RUN_CREW:
                raise ValueError(
                    f"Start method action '{self.action}' is not supported"
                )
            if self.action == MethodAction.RUN_CREW and not self.crew:
                raise ValueError(
                    "Start method with run_crew action must specify a crew"
                )

        elif self.type == MethodType.LISTEN:
            # Listen methods can have listen_to, action, update_state
            if not self.listen_to:
                raise ValueError("Listen method must specify listen_to targets")
            if self.action and self.action != MethodAction.RUN_CREW:
                raise ValueError(
                    f"Listen method action '{self.action}' is not supported"
                )
            if self.action == MethodAction.RUN_CREW and not self.crew:
                raise ValueError(
                    "Listen method with run_crew action must specify a crew"
                )
            if self.logic and self.logic not in [MethodLogic.AND, MethodLogic.OR]:
                raise ValueError(f"Listen method logic '{self.logic}' is not supported")

        elif self.type == MethodType.ROUTER:
            # Router methods can have listen_to, condition, routes
            if not self.listen_to:
                raise ValueError("Router method must specify listen_to targets")
            if not self.condition:
                raise ValueError("Router method must specify a condition")
            if not self.routes:
                raise ValueError("Router method must specify routes")

        return self


class FlowMethodsConfig(BaseModel):
    """Configuration for flow methods collection"""

    flow_methods: List[FlowMethodConfig] = Field(
        default_factory=list, description="List of flow method configurations"
    )

    @model_validator(mode="after")
    def validate_method_names_unique(self):
        """Validate that method names are unique"""
        method_names = [method.name for method in self.flow_methods]
        if len(method_names) != len(set(method_names)):
            raise ValueError("Flow method names must be unique")
        return self

    @model_validator(mode="after")
    def validate_method_dependencies(self):
        """Validate that referenced methods exist"""
        method_names = {method.name for method in self.flow_methods}

        for method in self.flow_methods:
            if method.listen_to:
                for target in method.listen_to:
                    if target not in method_names:
                        raise ValueError(
                            f"Method '{method.name}' references undefined method '{target}'"
                        )

        return self
