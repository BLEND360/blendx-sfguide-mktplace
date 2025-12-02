"""
Flow YAML Configuration Model

This module contains the FlowYAMLConfig model for validating complete flow configurations.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from app.crewai.models.agent_models import AgentConfig
from app.crewai.models.crew_models import CrewDefinition
from app.crewai.models.method_models import FlowMethodConfig, FlowMethodsConfig
from app.crewai.models.task_models import TaskConfig


class FlowConfig(BaseModel):
    """Configuration for the main flow"""

    # Flow configuration
    flow_name: Optional[str] = Field(None, description="Name of the flow")
    verbose: Optional[bool] = Field(
        True, description="Enable detailed logging for the flow"
    )
    class_name: str = Field(None, description="Custom class name for the flow")
    crews: List[str] = Field(
        ..., description="List of crew names to be used in the flow"
    )


class FlowYAMLConfig(BaseModel):
    """Complete flow configuration from YAML"""

    # Flow configuration
    flow: FlowConfig = Field(..., description="Main flow configuration")

    # Optional execution group name
    execution_group_name: Optional[str] = Field(
        None, description="Optional execution group name for organizing crews"
    )

    # Optional type
    type: Optional[str] = Field(
        None, description="Type of the flow execution (e.g., 'RAG')"
    )

    # Crew definitions (same as CrewYAMLConfig)
    crews: List[CrewDefinition] = Field(..., description="List of crew definitions")

    # Agent definitions (same as CrewYAMLConfig)
    agents: List[AgentConfig] = Field(
        ..., min_length=1, description="List of agent configurations"
    )

    # Task definitions (same as CrewYAMLConfig)
    tasks: List[TaskConfig] = Field(
        ..., min_length=1, description="List of task configurations"
    )

    # Flow methods (optional) - can be a list or FlowMethodsConfig
    flow_methods: Optional[Union[List[FlowMethodConfig], FlowMethodsConfig]] = Field(
        None, description="Flow methods configuration"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        """Validate that type is either None or 'RAG'"""
        if v is not None and v != "RAG":
            raise ValueError(
                f"Invalid type '{v}'. The 'type' field must be either None, missing, or 'RAG'"
            )
        return v

    @model_validator(mode="after")
    def normalize_flow_methods(self):
        """Normalize flow_methods to always be a FlowMethodsConfig"""
        if self.flow_methods is not None:
            if isinstance(self.flow_methods, list):
                # Convert list to FlowMethodsConfig
                self.flow_methods = FlowMethodsConfig(flow_methods=self.flow_methods)
        return self

    @model_validator(mode="after")
    def validate_flow_crew_consistency(self):
        """Validate consistency between flow crews and crew definitions"""
        # Get all crew names
        crew_names = {crew.name for crew in self.crews}

        # Check that all crews referenced in flow exist
        for crew_name in self.flow.crews:
            if crew_name not in crew_names:
                raise ValueError(f"Flow references unknown crew: {crew_name}")

        return self

    @model_validator(mode="after")
    def validate_crew_agent_task_consistency(self):
        """Validate consistency between crews, agents, and tasks"""
        # Get all agent roles
        agent_roles = {agent.role for agent in self.agents}
        task_names = {task.name for task in self.tasks}

        # Check that all crews reference valid agent roles and task names
        for crew in self.crews:
            for agent_role in crew.agents:
                if agent_role not in agent_roles:
                    raise ValueError(
                        f"Crew '{crew.name}' references unknown agent role: {agent_role}"
                    )

            for task_name in crew.tasks:
                if task_name not in task_names:
                    raise ValueError(
                        f"Crew '{crew.name}' references unknown task: {task_name}"
                    )

        # Check that all tasks in context exist
        for task in self.tasks:
            for context_task in task.context:
                if context_task not in task_names:
                    raise ValueError(
                        f"Task '{task.name}' references unknown context task: {context_task}"
                    )

        return self

    @model_validator(mode="after")
    def validate_flow_methods_crew_references(self):
        """Validate that flow methods reference valid crews"""
        if not self.flow_methods:
            return self

        crew_names = {crew.name for crew in self.crews}

        for method in self.flow_methods.flow_methods:
            if method.crew and method.crew not in crew_names:
                raise ValueError(
                    f"Flow method '{method.name}' references unknown crew: {method.crew}"
                )

        return self
