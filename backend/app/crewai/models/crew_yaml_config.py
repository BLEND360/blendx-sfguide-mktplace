"""
Crew YAML Configuration Model

This module contains the CrewYAMLConfig model for validating complete crew configurations.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.crewai.models.agent_models import AgentConfig
from app.crewai.models.crew_models import CrewDefinition
from app.crewai.models.task_models import TaskConfig


class CrewYAMLConfig(BaseModel):
    """Complete crew configuration from YAML"""

    execution_group_name: Optional[str] = Field(
        None, description="Optional execution group name for organizing crews"
    )
    type: Optional[str] = Field(
        None, description="Type of the execution group (e.g., 'RAG')"
    )
    crews: List[CrewDefinition] = Field(..., description="List of crew definitions")
    agents: List[AgentConfig] = Field(
        ..., min_length=1, description="List of agent configurations"
    )
    tasks: List[TaskConfig] = Field(
        ..., min_length=1, description="List of task configurations"
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

        # Check that tasks assigned to crews have agents that are part of those crews
        for crew in self.crews:
            crew_agents = set(crew.agents)
            for task_name in crew.tasks:
                # Find the task
                task = next((t for t in self.tasks if t.name == task_name), None)
                if task and task.agent:
                    if task.agent not in crew_agents:
                        raise ValueError(
                            f"Task '{task.name}' in crew '{crew.name}' references agent '{task.agent}' "
                            f"which is not part of this crew. Available agents: {list(crew_agents)}"
                        )

        return self
