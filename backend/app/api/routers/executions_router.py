"""
Workflow Execution Router

This module provides endpoints for executing crews and flows from YAML configuration
without persisting any data to the database. Useful for testing, development, and
scenarios where execution tracking is not required.
"""

import asyncio
import logging
import uuid
from functools import partial
from typing import Any, Dict, Optional

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, ValidationError

from app.api.utils.yaml_validation import (
    validate_execution_group_configuration,
    validate_flow_configuration,
)
from app.crewai.engine.builders.build_engine import CrewAIEngineConfig
from app.crewai.models.error_formatter import format_yaml_validation_error
from app.crewai.utils.parameter_substitution import substitute_parameters

router = APIRouter(prefix="/executions", tags=["Executions"])
logger = logging.getLogger(__name__)

# In-memory storage for execution results
_executions: Dict[str, Dict[str, Any]] = {}


class ExecutionRequest(BaseModel):
    """Request model for workflow execution."""

    yaml_text: str
    input: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None
    workflow_id: Optional[str] = None  # Optional workflow ID to associate with execution


class ExecutionAsyncResponse(BaseModel):
    """Response model for async execution initiation."""

    execution_id: str


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""

    execution_id: str
    status: str
    result: Optional[Any] = None


# -----------------------------------------------------------------------------
# Helper functions for execution
# -----------------------------------------------------------------------------


def _process_result(result: Any, obj: Any) -> str:
    """Process the result from a crew or flow execution."""
    if hasattr(result, "raw"):
        final_result = result.raw
    elif hasattr(result, "json_dict"):
        final_result = str(result.json_dict)
    elif isinstance(result, str):
        final_result = result
    elif hasattr(result, "values"):
        vals = list(result.values())
        final_result = vals[-1] if vals else "No results returned"
    else:
        final_result = str(result)

    if not final_result or str(final_result).lower() in {"", "none", "success"}:
        if hasattr(obj, "state"):
            for _attr in ("final_report", "process_output", "output", "result"):
                if hasattr(obj.state, _attr):
                    _state_val = getattr(obj.state, _attr)
                    if _state_val:
                        final_result = str(_state_val)
                        break

    return final_result


def _run_single_crew(crew) -> str:
    """Run a single crew without persistence."""
    crew_name = getattr(crew, "name", None) or "Unnamed Crew"

    try:
        logger.info(f"Started crew execution: {crew_name}")
        result = crew.kickoff()
        final_result = _process_result(result, crew)
        logger.info(f"Completed crew execution: {crew_name}")
        return final_result
    except Exception as e:
        error_message = f"Error in crew '{crew_name}': {str(e)}"
        logger.error(f"Error in crew execution {crew_name}: {str(e)}")
        return error_message


async def _run_crews(crews: list) -> list[str]:
    """Run crews without any database persistence."""
    tasks = []
    for crew in crews:
        run_crew_partial = partial(_run_single_crew, crew)
        task = asyncio.create_task(asyncio.to_thread(run_crew_partial))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return list(results)


async def _run_flow(flow, flow_name: str, inputs: Optional[dict]) -> str:
    """Run a flow without any database persistence."""
    try:
        logger.info(f"Started flow execution: {flow_name}")
        if inputs:
            result = await flow.kickoff_async(inputs=inputs)
        else:
            result = await flow.kickoff_async()
        final_result = _process_result(result, flow)
        logger.info(f"Completed flow execution: {flow_name}")
        return final_result
    except Exception as e:
        error_message = f"Error in flow '{flow_name}': {str(e)}"
        logger.error(f"Error in flow execution {flow_name}: {str(e)}")
        return error_message


# -----------------------------------------------------------------------------
# Crew Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/run-crew-async",
    summary="Execute crews from YAML config asynchronously without persistence",
    response_model=ExecutionAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_crew_async(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
) -> ExecutionAsyncResponse:
    """
    Execute crews from YAML configuration asynchronously without persisting any data.

    Returns an execution_id that can be used to poll for status/results.
    """
    execution_id = str(uuid.uuid4())

    # Validate configuration
    try:
        validate_execution_group_configuration(request.yaml_text)
    except ValueError as e:
        logger.error(f"Configuration type validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        processed_yaml = substitute_parameters(request.yaml_text, request.parameters)
        crews_config = CrewAIEngineConfig(
            config_text=processed_yaml, orchestration_type="crew"
        )
    except (ValidationError, yaml.YAMLError) as e:
        formatted_error = format_yaml_validation_error(str(e))
        logger.error(f"YAML or validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=formatted_error
        )
    except Exception as e:
        logger.error(f"Unexpected error during crew configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during crew configuration: {str(e)}",
        )

    # Initialize execution tracking
    _executions[execution_id] = {
        "status": "RUNNING",
        "result": None,
    }

    async def background_run() -> None:
        try:
            crews = crews_config.create_crews(input=request.input)
            results = await _run_crews(crews)
            _executions[execution_id] = {
                "status": "COMPLETED",
                "result": results,
            }
        except Exception as e:
            logger.error(f"Error running crew: {str(e)}")
            _executions[execution_id] = {
                "status": "FAILED",
                "result": f"Error: {str(e)}",
            }
        finally:
            crews_config.cleanup()

    background_tasks.add_task(background_run)
    return ExecutionAsyncResponse(execution_id=execution_id)


# -----------------------------------------------------------------------------
# Flow Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/run-flow-async",
    summary="Execute flow from YAML config asynchronously without persistence",
    response_model=ExecutionAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_flow_async(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
) -> ExecutionAsyncResponse:
    """
    Execute a flow from YAML configuration asynchronously without persisting any data.

    Returns an execution_id that can be used to poll for status/results.
    """
    execution_id = str(uuid.uuid4())

    # Validate configuration
    try:
        validate_flow_configuration(request.yaml_text)
    except ValueError as e:
        logger.error(f"Configuration type validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        processed_yaml = substitute_parameters(request.yaml_text, request.parameters)
        flow_config = CrewAIEngineConfig(
            config_text=processed_yaml,
            flow_id=execution_id,
            orchestration_type="flow",
        )
    except (ValidationError, yaml.YAMLError) as e:
        formatted_error = format_yaml_validation_error(str(e))
        logger.error(f"YAML or validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=formatted_error
        )
    except Exception as e:
        logger.error(f"Unexpected error during flow configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during flow configuration: {str(e)}",
        )

    # Initialize execution tracking
    _executions[execution_id] = {
        "status": "RUNNING",
        "result": None,
    }

    async def background_run() -> None:
        try:
            flow_name = flow_config.get_flow_name()
            flow = flow_config.create_flow(input=request.input)

            # Set flow ID and workflow_id in state if possible
            try:
                if hasattr(flow.state, "id"):
                    flow.state.id = execution_id
                elif isinstance(flow.state, dict):
                    flow.state["id"] = execution_id

                # Set workflow_id if provided
                if request.workflow_id:
                    if hasattr(flow.state, "workflow_id"):
                        flow.state.workflow_id = request.workflow_id
                    elif isinstance(flow.state, dict):
                        flow.state["workflow_id"] = request.workflow_id
            except Exception:
                pass

            inputs = {"input": request.input} if request.input else None
            result = await _run_flow(flow, flow_name, inputs)
            _executions[execution_id] = {
                "status": "COMPLETED",
                "result": result,
            }
        except Exception as e:
            logger.error(f"Error running flow: {str(e)}")
            _executions[execution_id] = {
                "status": "FAILED",
                "result": f"Error: {str(e)}",
            }
        finally:
            flow_config.cleanup()

    background_tasks.add_task(background_run)
    return ExecutionAsyncResponse(execution_id=execution_id)


# -----------------------------------------------------------------------------
# Polling Endpoint
# -----------------------------------------------------------------------------


@router.get(
    "/status/{execution_id}",
    summary="Get status and result of an execution",
    response_model=ExecutionStatusResponse,
)
async def get_execution_status(execution_id: str) -> ExecutionStatusResponse:
    """
    Get the status and result of a workflow execution.

    Poll this endpoint to check if an async execution has completed.
    """
    execution = _executions.get(execution_id)

    if execution is None:
        return ExecutionStatusResponse(
            execution_id=execution_id,
            status="NOT_FOUND",
            result=None,
        )

    return ExecutionStatusResponse(
        execution_id=execution_id,
        status=execution["status"],
        result=execution["result"],
    )


@router.delete(
    "/status/{execution_id}",
    summary="Delete execution result from memory",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_execution_status(execution_id: str) -> None:
    """
    Delete an execution result from memory.

    Use this to clean up completed executions and free memory.
    """
    if execution_id in _executions:
        del _executions[execution_id]
