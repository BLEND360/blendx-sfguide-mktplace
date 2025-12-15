"""
Crew Router.

Endpoints for crew execution management.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.models.crew_models import (
    CrewExecutionItem,
    CrewExecutionsResponse,
    CrewStartResponse,
    CrewStatusResponse,
)
from app.database.db import get_db
from app.services.crew_service import CrewService

router = APIRouter(prefix="/crew", tags=["Crew"])
logger = logging.getLogger(__name__)


@router.post("/start", response_model=CrewStartResponse)
async def start_crew_execution(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        service = CrewService(db)
        execution_id = service.create_execution_record(
            is_test=True,  # Mark as test execution from UI
        )

        background_tasks.add_task(service.run_crew_background, execution_id)

        return CrewStartResponse(
            execution_id=execution_id,
            status="PROCESSING",
            message="Crew execution started successfully",
        )

    except Exception as e:
        logger.error(f"Error starting crew execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start crew execution: {str(e)}")


@router.post("/start-external-tool", response_model=CrewStartResponse)
async def start_external_tool_crew_execution(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Inicia la ejecución de la crew con herramientas externas (Serper) en background.

    Steps:
    1. Generates UUID
    2. Create registry in the DB with status='PROCESSING'
    3. executes background task
    4. Returns id immediately
    """
    try:
        service = CrewService(db)
        execution_id = service.create_execution_record(
            crew_type="external_tool",
            is_test=True,  # Mark as test execution from UI
        )

        background_tasks.add_task(service.run_external_tool_crew_background, execution_id)

        return CrewStartResponse(
            execution_id=execution_id,
            status="PROCESSING",
            message="External tool crew execution started successfully",
        )

    except Exception as e:
        logger.error(f"Error starting external tool crew execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start external tool crew execution: {str(e)}")


@router.get("/status/{execution_id}", response_model=CrewStatusResponse)
async def get_crew_status(execution_id: str, db: Session = Depends(get_db)):
    """
    Endpoint de polling para consultar el estado de una ejecución.

    Returns:
    - Si status='PROCESSING': retorna status processing
    - Si status='COMPLETED': retorna el resultado completo
    - Si status='ERROR': retorna el error
    - Si no existe el ID: retorna 404
    """
    try:
        service = CrewService(db)
        result = service.get_execution_status(execution_id)

        if result is None:
            raise HTTPException(status_code=404, detail=f"Execution ID {execution_id} not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving crew status for {execution_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve status: {str(e)}")


@router.get("/executions", response_model=CrewExecutionsResponse)
async def list_crew_executions(
    limit: int = 10,
    is_test: bool | None = None,
    db: Session = Depends(get_db),
):
    """
    List latest crew executions.

    Args:
        limit: Maximum number of executions to return
        is_test: Filter by test flag (True for test executions only, False for non-test, None for all)
    """
    try:
        service = CrewService(db)
        executions = service.list_executions(limit, is_test=is_test)

        return CrewExecutionsResponse(
            executions=[CrewExecutionItem(**exec_data) for exec_data in executions]
        )

    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")


@router.get("/executions/workflow/{workflow_id}", response_model=CrewExecutionsResponse)
async def list_executions_by_workflow(
    workflow_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    List executions for a specific workflow.

    Args:
        workflow_id: The workflow ID to filter by
        limit: Maximum number of executions to return
    """
    try:
        service = CrewService(db)
        executions = service.list_executions_by_workflow(workflow_id, limit)

        return CrewExecutionsResponse(
            executions=[CrewExecutionItem(**exec_data) for exec_data in executions]
        )

    except Exception as e:
        logger.error(f"Error listing executions for workflow {workflow_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")
