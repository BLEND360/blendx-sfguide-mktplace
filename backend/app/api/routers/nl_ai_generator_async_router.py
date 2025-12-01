"""
Async Natural Language AI Generator Router

This module provides async API endpoints for natural language workflow generation
without requiring the chat mechanism. Reuses the existing workflows table.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.models.nl_ai_generator_async_models import (
    NLAIGeneratorAsyncRequest,
    NLAIGeneratorAsyncResponse,
    WorkflowGetResponse,
    WorkflowData,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _process_workflow_generation_background(
    workflow_id: str,
    user_request: str,
    user_id: Optional[str] = None,
    max_tokens: int = 4000,
    max_retries: int = 3,
) -> None:
    """
    Background task to process workflow generation.

    Args:
        workflow_id: The workflow identifier
        user_request: Natural language description of desired AI workflow
        user_id: Optional user identifier for tracking
        max_tokens: Maximum tokens for LLM response
        max_retries: Maximum number of retry attempts
    """
    try:
        # Import the sync version of generate_nl_ai_payload
        from app.services.nl_ai_generator_service import generate_nl_ai_payload

        # Use the sync implementation since background tasks run in threads
        payload_result, error = generate_nl_ai_payload(
            user_request=user_request,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )

        if error:
            # Update workflow status to FAILED
            from app.database.db import get_new_db_session
            from app.database.repositories.workflows_repository import (
                WorkflowsRepository,
            )

            with get_new_db_session() as db:
                workflow_repo = WorkflowsRepository(db)
                workflow_repo.update_workflow(
                    workflow_id,
                    1,
                    {
                        "status": "FAILED",
                        "rationale": f"Generation failed: {error}",
                    },
                )
            return

        # Extract workflow data from AI payload
        payload = payload_result.get("payload", {})

        # Update workflow with completed data
        from app.database.db import get_new_db_session
        from app.database.repositories.workflows_repository import WorkflowsRepository

        with get_new_db_session() as db:
            workflow_repo = WorkflowsRepository(db)

            # Check if workflow already has a title to preserve it (for versioning)
            existing = workflow_repo.get_workflow(workflow_id)
            title = None
            if existing and getattr(existing, "title", None):
                # Keep the same title for versions of the same workflow
                title = existing.title
            else:
                # New workflow - need to check for duplicate titles
                title = payload_result.get("title")

                # Only check for duplicates if we have both title and user_id
                if title and user_id:
                    # Check if title exists for this user (excluding current workflow)
                    counter = 1
                    original_title = title
                    while workflow_repo.check_title_exists_for_user(
                        title, user_id, exclude_workflow_id=workflow_id
                    ):
                        counter += 1
                        title = f"{original_title} ({counter})"
                        # Safety check to avoid infinite loop
                        if counter > 100:
                            title = f"{original_title} ({workflow_id[:8]})"
                            break

            workflow_repo.update_workflow(
                workflow_id,
                1,
                {
                    "type": payload_result.get("type", ""),
                    "mermaid": payload_result.get("mermaid_chart", ""),
                    "title": title,
                    "status": "COMPLETED",
                    "rationale": payload_result.get("rationale", ""),
                    "yaml_text": payload.get("yaml_text", ""),
                    "model": payload_result.get("model", "gpt-4o"),
                    "user_id": user_id,  # Ensure user_id is stored
                },
            )

    except Exception as e:
        logger.error(f"Background workflow generation failed for {workflow_id}: {e}")
        # Update workflow status to FAILED
        from app.database.db import get_new_db_session
        from app.database.repositories.workflows_repository import WorkflowsRepository

        try:
            with get_new_db_session() as db:
                workflow_repo = WorkflowsRepository(db)
                workflow_repo.update_workflow(
                    workflow_id,
                    1,
                    {
                        "status": "FAILED",
                        "rationale": f"Generation failed: {str(e)}",
                    },
                )
        except Exception as update_error:
            logger.error(f"Failed to update workflow status to FAILED: {update_error}")


@router.post(
    "/nl-ai-generator-async",
    response_model=NLAIGeneratorAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["NL AI Generator"],
    summary="Generate workflow from natural language (async)",
    description="Generate a workflow from natural language request asynchronously. "
    "Returns immediately with workflow_id for polling. Reuses the workflows table without requiring chat mechanism.",
)
async def nl_ai_generator_async_endpoint(
    request: NLAIGeneratorAsyncRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate a workflow from natural language request asynchronously.

    This endpoint:
    - Returns immediately with workflow_id
    - Processes generation in background
    - Saves results to the workflows table
    - Supports both CrewAI and FlowAI configurations
    - Reuses existing title if workflow already exists
    - Works without chat mechanism

    Args:
        request: NL generator request with user input and optional parameters
        background_tasks: FastAPI background tasks

    Returns:
        NLAIGeneratorAsyncResponse: Workflow ID for polling

    Raises:
        HTTPException: If request is invalid
    """
    try:
        # Generate workflow_id
        workflow_id = str(uuid.uuid4())

        # Add background task
        background_tasks.add_task(
            _process_workflow_generation_background,
            workflow_id=workflow_id,
            user_request=request.user_request,
            user_id=request.user_id,
            max_tokens=4000,
            max_retries=3,
        )

        # Create workflow with PENDING status immediately
        from app.database.db import get_new_db_session
        from app.database.repositories.workflows_repository import WorkflowsRepository

        with get_new_db_session() as db:
            workflow_repo = WorkflowsRepository(db)
            workflow_repo.create_workflow(
                {
                    "workflow_id": workflow_id,
                    "type": "run-build-crew",  # Default type, will be updated by background task
                    "mermaid": "",
                    "title": None,
                    "status": "PENDING",
                    "rationale": None,
                    "yaml_text": "",
                    "chat_id": None,
                    "message_id": None,
                    "user_id": request.user_id,
                    "model": "gpt-4o",
                    "stable": True,
                }
            )

        return NLAIGeneratorAsyncResponse(
            workflow_id=workflow_id,
            status="PENDING",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in async NL generator: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/nl-ai-generator-async/{workflow_id}",
    response_model=WorkflowGetResponse,
    tags=["NL AI Generator"],
    summary="Get workflow generation result",
    description="Get the result of an async workflow generation by workflow_id. "
    "Use this endpoint to poll for the status and retrieve the completed workflow.",
)
async def get_workflow_result(workflow_id: str):
    """
    Get the result of an async workflow generation.

    This endpoint:
    - Returns the current status and data of the workflow
    - Can be used to poll for completion after submitting an async request
    - Returns PENDING while processing, COMPLETED when done, or FAILED on error

    Args:
        workflow_id: The workflow identifier returned from the async endpoint

    Returns:
        WorkflowGetResponse: Workflow data if found

    Raises:
        HTTPException: If workflow not found or server error
    """
    try:
        from app.database.db import get_new_db_session
        from app.database.repositories.workflows_repository import WorkflowsRepository

        with get_new_db_session() as db:
            workflow_repo = WorkflowsRepository(db)
            workflow = workflow_repo.get_workflow(workflow_id)

            if not workflow:
                return WorkflowGetResponse(workflow=None, found=False)

            workflow_data = WorkflowData(
                workflow_id=workflow.workflow_id,
                version=workflow.version,
                type=workflow.type,
                status=workflow.status,
                mermaid=workflow.mermaid,
                title=workflow.title,
                rationale=workflow.rationale or "",
                yaml_text=workflow.yaml_text or "",
                user_id=workflow.user_id,
                model=workflow.model,
                stable=workflow.stable,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at,
            )

            return WorkflowGetResponse(workflow=workflow_data, found=True)

    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
