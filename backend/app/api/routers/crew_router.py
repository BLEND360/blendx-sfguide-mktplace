"""
Crew Router.

Endpoints for crew execution management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.models.crew_models import (
    CrewExecutionItem,
    CrewExecutionsResponse,
    CrewStatusResponse,
)
from app.database.db import get_db
from app.services.crew_service import CrewService

router = APIRouter(prefix="/crew", tags=["Crew"])
logger = logging.getLogger(__name__)


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
