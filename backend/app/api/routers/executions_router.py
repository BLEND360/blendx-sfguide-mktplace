"""
Workflow Execution Router

This module provides endpoints for executing crews and flows from YAML configuration.
Flow executions are persisted to the database for status tracking. Crew executions
are stored in-memory only.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.api.utils.yaml_validation import (
    validate_execution_group_configuration,
    validate_flow_configuration,
)
from app.crewai.engine.builders.build_engine import CrewAIEngineConfig
from app.crewai.models.error_formatter import format_yaml_validation_error
from app.crewai.utils.parameter_substitution import substitute_parameters
from app.database.db import get_db, get_new_db_session
from app.database.models.flow_executions import FlowExecution
from app.database.models.execution_groups import ExecutionGroup
from app.database.utils.enums import StatusEnum

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


class ExecutionItem(BaseModel):
    """Response model for a single execution item in list."""

    execution_id: str
    status: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    workflow_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ExecutionsListResponse(BaseModel):
    """Response model for list of executions."""

    executions: List[ExecutionItem]


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
    summary="Execute crews from YAML config asynchronously",
    response_model=ExecutionAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_crew_async(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ExecutionAsyncResponse:
    """
    Execute crews from YAML configuration asynchronously.

    Persists execution status to database and returns an execution_id
    that can be used to poll for status/results.
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

    # Initialize execution tracking in memory
    _executions[execution_id] = {
        "status": "RUNNING",
        "result": None,
    }

    # Persist execution to database with PENDING status
    crew_name = crews_config.get_crew_name() if hasattr(crews_config, 'get_crew_name') else None
    try:
        execution_group = ExecutionGroup(
            id=execution_id,
            workflow_id=request.workflow_id,
            name=crew_name,
            status=StatusEnum.PENDING,
        )
        db.add(execution_group)
        db.commit()
        logger.info(f"Created execution group record: {execution_id}")
    except Exception as e:
        logger.error(f"Failed to persist execution group to database: {str(e)}")
        db.rollback()

    async def background_run() -> None:
        bg_db = None
        try:
            # Update database status to RUNNING
            try:
                bg_db = get_new_db_session()
                exec_group = bg_db.query(ExecutionGroup).filter(ExecutionGroup.id == execution_id).first()
                if exec_group:
                    exec_group.status = StatusEnum.RUNNING
                    bg_db.commit()
                    logger.info(f"Updated execution group {execution_id} to RUNNING")
            except Exception as db_e:
                logger.error(f"Failed to update execution group status to RUNNING: {str(db_e)}")
                if bg_db:
                    bg_db.rollback()

            crews = crews_config.create_crews(input=request.input)
            results = await _run_crews(crews)
            _executions[execution_id] = {
                "status": "COMPLETED",
                "result": results,
            }

            # Update database with completed status
            try:
                bg_db = get_new_db_session()
                exec_group = bg_db.query(ExecutionGroup).filter(ExecutionGroup.id == execution_id).first()
                if exec_group:
                    exec_group.status = StatusEnum.COMPLETED
                    exec_group.result = str(results) if results else None
                    exec_group.finished_at = datetime.utcnow()
                    bg_db.commit()
                    logger.info(f"Updated execution group {execution_id} to COMPLETED")
            except Exception as db_e:
                logger.error(f"Failed to update execution group status in database: {str(db_e)}")
                if bg_db:
                    bg_db.rollback()

        except Exception as e:
            logger.error(f"Error running crew: {str(e)}")
            error_result = f"Error: {str(e)}"
            _executions[execution_id] = {
                "status": "FAILED",
                "result": error_result,
            }

            # Update database with failed status
            try:
                if bg_db is None:
                    bg_db = get_new_db_session()
                exec_group = bg_db.query(ExecutionGroup).filter(ExecutionGroup.id == execution_id).first()
                if exec_group:
                    exec_group.status = StatusEnum.FAILED
                    exec_group.result = error_result
                    exec_group.finished_at = datetime.utcnow()
                    bg_db.commit()
                    logger.info(f"Updated execution group {execution_id} to FAILED")
            except Exception as db_e:
                logger.error(f"Failed to update execution group status in database: {str(db_e)}")
                if bg_db:
                    bg_db.rollback()

        finally:
            crews_config.cleanup()
            if bg_db:
                bg_db.close()

    background_tasks.add_task(background_run)
    return ExecutionAsyncResponse(execution_id=execution_id)


# -----------------------------------------------------------------------------
# Flow Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/run-flow-async",
    summary="Execute flow from YAML config asynchronously",
    response_model=ExecutionAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_flow_async(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ExecutionAsyncResponse:
    """
    Execute a flow from YAML configuration asynchronously.

    Persists execution status to database and returns an execution_id
    that can be used to poll for status/results.
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

    # Initialize execution tracking in memory
    _executions[execution_id] = {
        "status": "RUNNING",
        "result": None,
    }

    # Persist execution to database with PENDING status
    flow_name = flow_config.get_flow_name()
    try:
        flow_execution = FlowExecution(
            id=execution_id,
            workflow_id=request.workflow_id,
            name=flow_name,
            status=StatusEnum.PENDING,
        )
        db.add(flow_execution)
        db.commit()
        logger.info(f"Created flow execution record: {execution_id}")
    except Exception as e:
        logger.error(f"Failed to persist flow execution to database: {str(e)}")
        db.rollback()

    async def background_run() -> None:
        bg_db = None
        try:
            # Update database status to RUNNING
            try:
                bg_db = get_new_db_session()
                flow_exec = bg_db.query(FlowExecution).filter(FlowExecution.id == execution_id).first()
                if flow_exec:
                    flow_exec.status = StatusEnum.RUNNING
                    bg_db.commit()
                    logger.info(f"Updated flow execution {execution_id} to RUNNING")
            except Exception as db_e:
                logger.error(f"Failed to update flow execution status to RUNNING: {str(db_e)}")
                if bg_db:
                    bg_db.rollback()

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

            # Update database with completed status
            try:
                bg_db = get_new_db_session()
                flow_exec = bg_db.query(FlowExecution).filter(FlowExecution.id == execution_id).first()
                if flow_exec:
                    flow_exec.status = StatusEnum.COMPLETED
                    flow_exec.result = result
                    flow_exec.finished_at = datetime.utcnow()
                    bg_db.commit()
                    logger.info(f"Updated flow execution {execution_id} to COMPLETED")
            except Exception as db_e:
                logger.error(f"Failed to update flow execution status in database: {str(db_e)}")
                if bg_db:
                    bg_db.rollback()

        except Exception as e:
            logger.error(f"Error running flow: {str(e)}")
            error_result = f"Error: {str(e)}"
            _executions[execution_id] = {
                "status": "FAILED",
                "result": error_result,
            }

            # Update database with failed status
            try:
                if bg_db is None:
                    bg_db = get_new_db_session()
                flow_exec = bg_db.query(FlowExecution).filter(FlowExecution.id == execution_id).first()
                if flow_exec:
                    flow_exec.status = StatusEnum.FAILED
                    flow_exec.result = error_result
                    flow_exec.finished_at = datetime.utcnow()
                    bg_db.commit()
                    logger.info(f"Updated flow execution {execution_id} to FAILED")
            except Exception as db_e:
                logger.error(f"Failed to update flow execution status in database: {str(db_e)}")
                if bg_db:
                    bg_db.rollback()

        finally:
            flow_config.cleanup()
            if bg_db:
                bg_db.close()

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
async def get_execution_status(
    execution_id: str,
    db: Session = Depends(get_db),
) -> ExecutionStatusResponse:
    """
    Get the status and result of a workflow execution.

    Poll this endpoint to check if an async execution has completed.
    First checks in-memory cache, then falls back to database.
    """
    # First check in-memory cache
    execution = _executions.get(execution_id)

    if execution is not None:
        return ExecutionStatusResponse(
            execution_id=execution_id,
            status=execution["status"],
            result=execution["result"],
        )

    # Fall back to database lookup for flow executions
    try:
        flow_exec = db.query(FlowExecution).filter(FlowExecution.id == execution_id).first()
        if flow_exec:
            status_str = flow_exec.status.name if flow_exec.status else "UNKNOWN"
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=status_str,
                result=flow_exec.result,
            )
    except Exception as e:
        logger.error(f"Error querying flow_executions for {execution_id}: {str(e)}")

    # Fall back to database lookup for execution groups (crews)
    try:
        exec_group = db.query(ExecutionGroup).filter(ExecutionGroup.id == execution_id).first()
        if exec_group:
            status_str = exec_group.status.name if exec_group.status else "UNKNOWN"
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=status_str,
                result=exec_group.result,
            )
    except Exception as e:
        logger.error(f"Error querying execution_groups for {execution_id}: {str(e)}")

    return ExecutionStatusResponse(
        execution_id=execution_id,
        status="NOT_FOUND",
        result=None,
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


# -----------------------------------------------------------------------------
# List Executions by Workflow ID
# -----------------------------------------------------------------------------


@router.get(
    "/flow/workflow/{workflow_id}",
    summary="List flow executions for a workflow",
    response_model=ExecutionsListResponse,
)
async def list_flow_executions_by_workflow(
    workflow_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> ExecutionsListResponse:
    """
    List flow executions for a specific workflow.

    Args:
        workflow_id: The workflow ID to filter by
        limit: Maximum number of executions to return (default: 20)
    """
    try:
        executions = (
            db.query(FlowExecution)
            .filter(FlowExecution.workflow_id == workflow_id)
            .order_by(FlowExecution.created_at.desc())
            .limit(limit)
            .all()
        )

        return ExecutionsListResponse(
            executions=[
                ExecutionItem(
                    execution_id=exec.id,
                    status=exec.status.name if exec.status else "UNKNOWN",
                    name=exec.name,
                    created_at=exec.created_at,
                    updated_at=exec.updated_at,
                    workflow_id=exec.workflow_id,
                )
                for exec in executions
            ]
        )
    except Exception as e:
        logger.error(f"Error listing flow executions for workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list flow executions: {str(e)}",
        )


@router.get(
    "/group/workflow/{workflow_id}",
    summary="List execution groups for a workflow",
    response_model=ExecutionsListResponse,
)
async def list_group_executions_by_workflow(
    workflow_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> ExecutionsListResponse:
    """
    List execution groups for a specific workflow.

    Args:
        workflow_id: The workflow ID to filter by
        limit: Maximum number of executions to return (default: 20)
    """
    try:
        executions = (
            db.query(ExecutionGroup)
            .filter(ExecutionGroup.workflow_id == workflow_id)
            .order_by(ExecutionGroup.created_at.desc())
            .limit(limit)
            .all()
        )

        return ExecutionsListResponse(
            executions=[
                ExecutionItem(
                    execution_id=exec.id,
                    status=exec.status.name if exec.status else "UNKNOWN",
                    name=exec.name,
                    created_at=exec.created_at,
                    updated_at=exec.updated_at,
                    workflow_id=exec.workflow_id,
                )
                for exec in executions
            ]
        )
    except Exception as e:
        logger.error(f"Error listing execution groups for workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list execution groups: {str(e)}",
        )


@router.get(
    "/flow/status/{execution_id}",
    summary="Get status of a flow execution",
    response_model=ExecutionStatusResponse,
)
async def get_flow_execution_status(
    execution_id: str,
    db: Session = Depends(get_db),
) -> ExecutionStatusResponse:
    """
    Get the status and result of a flow execution from database.
    """
    try:
        execution = db.query(FlowExecution).filter(FlowExecution.id == execution_id).first()

        if execution is None:
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status="NOT_FOUND",
                result=None,
            )

        return ExecutionStatusResponse(
            execution_id=execution.id,
            status=execution.status.name if execution.status else "UNKNOWN",
            result=execution.result,
        )
    except Exception as e:
        logger.error(f"Error getting flow execution status {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get flow execution status: {str(e)}",
        )


@router.get(
    "/group/status/{execution_id}",
    summary="Get status of an execution group",
    response_model=ExecutionStatusResponse,
)
async def get_group_execution_status(
    execution_id: str,
    db: Session = Depends(get_db),
) -> ExecutionStatusResponse:
    """
    Get the status and result of an execution group from database.
    """
    try:
        execution = db.query(ExecutionGroup).filter(ExecutionGroup.id == execution_id).first()

        if execution is None:
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status="NOT_FOUND",
                result=None,
            )

        return ExecutionStatusResponse(
            execution_id=execution.id,
            status=execution.status.name if execution.status else "UNKNOWN",
            result=execution.result,
        )
    except Exception as e:
        logger.error(f"Error getting execution group status {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution group status: {str(e)}",
        )
