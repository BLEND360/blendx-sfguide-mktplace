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
        crew_name: str,
        crew_type: str | None = None,
    ) -> str:
        """
        Create initial execution record in database.

        Args:
            crew_name: Name of the crew being executed
            crew_type: Optional type of crew (e.g., 'external_tool')

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
            (id, crew_name, status, metadata, result_text)
            SELECT
                :id,
                :crew_name,
                :status,
                PARSE_JSON(:metadata),
                :result_text
        """)

        self.db.execute(
            insert_query,
            {
                "id": execution_id,
                "crew_name": crew_name,
                "status": "PROCESSING",
                "metadata": metadata_json,
                "result_text": "Processing...",
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

    def list_executions(self, limit: int = 10) -> list[dict]:
        """
        List recent crew executions.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of execution dictionaries
        """
        query = text(f"""
            SELECT
                id,
                crew_name,
                status,
                execution_timestamp,
                updated_at
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
                    "crew_name": row[1],
                    "status": row[2],
                    "execution_timestamp": str(row[3]) if row[3] else None,
                    "updated_at": str(row[4]) if row[4] else None,
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

        session.execute(
            update_query,
            {
                "id": execution_id,
                "raw_output": raw_output_json,
                "result_text": result_text,
                "status": "COMPLETED",
                "metadata": metadata_json,
            },
        )
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
