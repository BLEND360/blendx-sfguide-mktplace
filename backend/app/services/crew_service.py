"""
Crew Service.

Business logic for crew execution management.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.models.crew_models import CrewStatusResponse
from app.config.settings import get_settings
from app.database.db import get_new_db_session
from app.examples.example_crew import run_crew
from app.examples.external_tool_crew import run_external_tool_crew
from app.handlers.lite_llm_handler import get_llm

logger = logging.getLogger(__name__)


def get_table_name() -> str:
    """Get the fully qualified table name from settings."""
    return get_settings().crew_execution_full_table_name


class CrewService:
    """Service for managing crew executions."""

    def __init__(self, db: Session):
        self.db = db

    def create_execution_record(
        self,
        crew_type: str | None = None,
        workflow_id: str | None = None,
        is_test: bool = False,
    ) -> str:
        """
        Create initial execution record in database.

        Args:
            crew_type: Optional type of crew (e.g., 'external_tool')
            workflow_id: Optional workflow ID to associate with this execution
            is_test: Flag to indicate if this is a test execution from UI

        Returns:
            Generated execution ID
        """
        execution_id = str(uuid.uuid4())
        logger.info(f"Creating execution record with ID: {execution_id}")

        metadata = {
            "model": "claude-3-5-sonnet",
            "provider": "snowflake",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        if crew_type:
            metadata["crew_type"] = crew_type

        metadata_json = json.dumps(metadata)

        insert_query = text(f"""
            INSERT INTO {get_table_name()}
            (id, status, metadata, result_text, workflow_id, is_test)
            SELECT
                :id,
                :status,
                PARSE_JSON(:metadata),
                :result_text,
                :workflow_id,
                :is_test
        """)

        self.db.execute(
            insert_query,
            {
                "id": execution_id,
                "status": "PROCESSING",
                "metadata": metadata_json,
                "result_text": "Processing...",
                "workflow_id": workflow_id,
                "is_test": is_test,
            },
        )
        self.db.commit()

        logger.info(f"Initial record created for {execution_id}")
        return execution_id

    def get_execution_status(self, execution_id: str) -> CrewStatusResponse | None:
        """
        Get the status of a crew execution.

        Args:
            execution_id: The execution ID to look up

        Returns:
            CrewStatusResponse or None if not found
        """
        query = text(f"""
            SELECT
                id,
                status,
                raw_output,
                result_text,
                metadata
            FROM {get_table_name()}
            WHERE id = :execution_id
        """)

        result = self.db.execute(query, {"execution_id": execution_id}).fetchone()

        if not result:
            return None

        row_id, status, raw_output, result_text, metadata = result

        if status == "PROCESSING":
            return CrewStatusResponse(
                execution_id=row_id,
                status="PROCESSING",
                result=None,
                error=None,
            )
        elif status == "COMPLETED":
            try:
                result_data = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            except:
                result_data = {"raw": str(raw_output)}

            return CrewStatusResponse(
                execution_id=row_id,
                status="COMPLETED",
                result=result_data,
                error=None,
            )
        elif status == "ERROR":
            return CrewStatusResponse(
                execution_id=row_id,
                status="ERROR",
                result=None,
                error=result_text,
            )
        else:
            return CrewStatusResponse(
                execution_id=row_id,
                status=status,
                result={"raw": result_text} if result_text else None,
                error=None,
            )

    def list_executions(self, limit: int = 10, is_test: bool | None = None) -> list[dict]:
        """
        List recent executions.

        Args:
            limit: Maximum number of executions to return
            is_test: Filter by test flag (True for test only, False for non-test, None for all)

        Returns:
            List of execution dictionaries
        """
        # Build query with optional is_test filter
        if is_test is not None:
            query = text(f"""
                SELECT
                    id,
                    status,
                    execution_timestamp,
                    updated_at,
                    workflow_id
                FROM {get_table_name()}
                WHERE is_test = :is_test
                ORDER BY execution_timestamp DESC
                LIMIT :limit
            """)
            results = self.db.execute(query, {"limit": limit, "is_test": is_test}).fetchall()
        else:
            query = text(f"""
                SELECT
                    id,
                    status,
                    execution_timestamp,
                    updated_at,
                    workflow_id
                FROM {get_table_name()}
                ORDER BY execution_timestamp DESC
                LIMIT :limit
            """)
            results = self.db.execute(query, {"limit": limit}).fetchall()

        executions = []
        for row in results:
            executions.append(
                {
                    "execution_id": row[0],
                    "status": row[1],
                    "execution_timestamp": str(row[2]) if row[2] else None,
                    "updated_at": str(row[3]) if row[3] else None,
                    "workflow_id": row[4],
                }
            )

        return executions

    def list_executions_by_workflow(self, workflow_id: str, limit: int = 10) -> list[dict]:
        """
        List executions for a specific workflow.

        Args:
            workflow_id: The workflow ID to filter by
            limit: Maximum number of executions to return

        Returns:
            List of execution dictionaries
        """
        query = text(f"""
            SELECT
                id,
                status,
                execution_timestamp,
                updated_at,
                workflow_id
            FROM {get_table_name()}
            WHERE workflow_id = :workflow_id
            ORDER BY execution_timestamp DESC
            LIMIT :limit
        """)
        results = self.db.execute(query, {"workflow_id": workflow_id, "limit": limit}).fetchall()

        executions = []
        for row in results:
            executions.append(
                {
                    "execution_id": row[0],
                    "status": row[1],
                    "execution_timestamp": str(row[2]) if row[2] else None,
                    "updated_at": str(row[3]) if row[3] else None,
                    "workflow_id": row[4],
                }
            )

        return executions

    @staticmethod
    async def run_crew_background(execution_id: str):
        """
        Background task que ejecuta la crew y guarda el resultado en la BD.
        """
        logger.info(f"Starting crew execution for ID: {execution_id}")

        try:
            with get_new_db_session() as session:
                llm = get_llm(provider="snowflake", model="claude-3-5-sonnet")
                logger.info(f"LLM initialized for execution {execution_id}")

                logger.info(f"Running crew for execution {execution_id}")
                crew_output = await run_crew(llm)
                logger.info(f"Crew execution completed for {execution_id}")

                result_text, raw_output = CrewService._extract_crew_output(crew_output)

                CrewService._save_success_result(
                    session,
                    execution_id,
                    result_text,
                    raw_output,
                )

        except Exception as e:
            logger.error(f"Error in crew execution {execution_id}: {str(e)}", exc_info=True)
            CrewService._save_error_result(execution_id, str(e))

    @staticmethod
    async def run_external_tool_crew_background(execution_id: str):
        """
        Background task que ejecuta la crew con herramientas externas y guarda el resultado en la BD.
        """
        logger.info(f"Starting external tool crew execution for ID: {execution_id}")

        try:
            with get_new_db_session() as session:
                llm = get_llm(provider="snowflake", model="claude-3-5-sonnet")
                logger.info(f"LLM initialized for external tool crew execution {execution_id}")

                logger.info(f"Running external tool crew for execution {execution_id}")
                crew_output = await run_external_tool_crew(llm)
                logger.info(f"External tool crew execution completed for {execution_id}")

                result_text, raw_output = CrewService._extract_crew_output(crew_output)

                CrewService._save_success_result(
                    session,
                    execution_id,
                    result_text,
                    raw_output,
                    crew_type="external_tool",
                )

        except Exception as e:
            logger.error(f"Error in external tool crew execution {execution_id}: {str(e)}", exc_info=True)
            CrewService._save_error_result(execution_id, str(e))

    @staticmethod
    def _extract_crew_output(crew_output) -> tuple[str, dict]:
        """Extract result_text and raw_output from crew output."""
        if hasattr(crew_output, "json_dict") and crew_output.json_dict:
            raw_output = crew_output.json_dict
            result_text = str(crew_output.json_dict)
        elif hasattr(crew_output, "raw"):
            result_text = crew_output.raw
            raw_output = {"raw": crew_output.raw}
        else:
            result_text = str(crew_output)
            raw_output = {"output": result_text}

        return result_text, raw_output

    @staticmethod
    def _save_success_result(
        session: Session,
        execution_id: str,
        result_text: str,
        raw_output: dict,
        crew_type: str | None = None,
        workflow_id: str | None = None,
    ):
        """Save successful execution result to database."""
        raw_output_json = json.dumps(raw_output)

        metadata = {
            "model": "claude-3-5-sonnet",
            "provider": "snowflake",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if crew_type:
            metadata["crew_type"] = crew_type

        metadata_json = json.dumps(metadata)

        # Build update query - only include workflow_id if provided
        if workflow_id:
            update_query = text(f"""
                UPDATE {get_table_name()}
                SET
                    raw_output = PARSE_JSON(:raw_output),
                    result_text = :result_text,
                    status = :status,
                    metadata = PARSE_JSON(:metadata),
                    workflow_id = :workflow_id,
                    updated_at = CURRENT_TIMESTAMP()
                WHERE id = :id
            """)
            params = {
                "id": execution_id,
                "raw_output": raw_output_json,
                "result_text": result_text,
                "status": "COMPLETED",
                "metadata": metadata_json,
                "workflow_id": workflow_id,
            }
        else:
            update_query = text(f"""
                UPDATE {get_table_name()}
                SET
                    raw_output = PARSE_JSON(:raw_output),
                    result_text = :result_text,
                    status = :status,
                    metadata = PARSE_JSON(:metadata),
                    updated_at = CURRENT_TIMESTAMP()
                WHERE id = :id
            """)
            params = {
                "id": execution_id,
                "raw_output": raw_output_json,
                "result_text": result_text,
                "status": "COMPLETED",
                "metadata": metadata_json,
            }

        session.execute(update_query, params)
        session.commit()

        logger.info(f"Crew result saved successfully for {execution_id}")

    @staticmethod
    def _save_error_result(execution_id: str, error_message: str):
        """Save error result to database."""
        try:
            with get_new_db_session() as session:
                error_query = text(f"""
                    UPDATE {get_table_name()}
                    SET
                        status = :status,
                        result_text = :error_message,
                        updated_at = CURRENT_TIMESTAMP()
                    WHERE id = :id
                """)

                session.execute(
                    error_query,
                    {
                        "id": execution_id,
                        "status": "ERROR",
                        "error_message": error_message,
                    },
                )
                session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status for {execution_id}: {str(db_error)}")

    @staticmethod
    def create_and_save_execution(
        result_text: str,
        raw_output: dict,
        workflow_id: str | None = None,
        is_test: bool = False,
        status: str = "COMPLETED",
    ) -> str:
        """
        Create a new execution record and save results in one operation.
        Used by flow executions that don't need the two-phase create/update pattern.

        Args:
            result_text: Text result from the execution
            raw_output: Raw output dictionary
            workflow_id: Optional workflow ID to associate
            is_test: Flag for test executions
            status: Execution status (default: COMPLETED)

        Returns:
            Generated execution ID
        """
        execution_id = str(uuid.uuid4())
        raw_output_json = json.dumps(raw_output)

        metadata = {
            "model": "claude-3-5-sonnet",
            "provider": "snowflake",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        metadata_json = json.dumps(metadata)

        try:
            with get_new_db_session() as session:
                insert_query = text(f"""
                    INSERT INTO {get_table_name()}
                    (id, status, metadata, result_text, raw_output, workflow_id, is_test)
                    SELECT
                        :id,
                        :status,
                        PARSE_JSON(:metadata),
                        :result_text,
                        PARSE_JSON(:raw_output),
                        :workflow_id,
                        :is_test
                """)

                session.execute(
                    insert_query,
                    {
                        "id": execution_id,
                        "status": status,
                        "metadata": metadata_json,
                        "result_text": result_text,
                        "raw_output": raw_output_json,
                        "workflow_id": workflow_id,
                        "is_test": is_test,
                    },
                )
                session.commit()

            logger.info(f"Created and saved execution {execution_id}")
            return execution_id

        except Exception as e:
            logger.error(f"Failed to create and save execution: {str(e)}")
            raise
