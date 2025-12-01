"""
Workflows Repository for BlendX Core.

Provides database operations for workflows generated through the natural language generator.
"""

import logging
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.models.workflows import Workflow

logger = logging.getLogger(__name__)


class WorkflowsRepository:
    """Repository for workflow database operations."""

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session

    def create_workflow(self, workflow_data: dict) -> Workflow:
        """
        Create a new workflow record in the database.

        Args:
            workflow_data: Dictionary with workflow data to create.

        Returns:
            The created Workflow instance.
        """
        try:
            # Take a shallow copy so caller mutations can't affect our params
            workflow_data = dict(workflow_data)

            # DEBUGGING: Check what yaml_text type is being received
            print(f"\n=== REPOSITORY DEBUG ===")
            print(
                f"workflow_data['yaml_text'] type: {type(workflow_data['yaml_text'])}"
            )
            print(
                f"workflow_data['yaml_text'] value: {str(workflow_data['yaml_text'])[:100]}..."
            )
            print(f"=== END REPOSITORY DEBUG ===\n")

            # Use raw SQL insert for Snowflake compatibility
            self.session.execute(
                text(
                    """
                    INSERT INTO workflows (workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at)
                    VALUES (:workflow_id, :version, :type, :mermaid, :title, :status, :rationale, :yaml_text, :chat_id, :message_id, :user_id, :model, :stable, CURRENT_TIMESTAMP())
                    """
                ),
                {
                    "workflow_id": workflow_data["workflow_id"],
                    "version": workflow_data.get("version", 1),
                    "type": workflow_data["type"],
                    "mermaid": workflow_data["mermaid"],
                    "title": workflow_data.get("title"),
                    "status": workflow_data.get("status", "PENDING"),
                    "rationale": workflow_data["rationale"],
                    "yaml_text": workflow_data["yaml_text"],
                    "chat_id": workflow_data["chat_id"],
                    "message_id": workflow_data["message_id"],
                    "user_id": workflow_data.get("user_id"),
                    "model": workflow_data.get("model"),
                    "stable": workflow_data.get("stable", True),
                },
            )
            self.session.commit()

            # Return the created workflow by querying it back
            return self.get_workflow(
                workflow_data["workflow_id"], workflow_data.get("version", 1)
            )

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating workflow: {e}")
            raise

    def get_workflow(
        self, workflow_id: str, version: Optional[int] = None
    ) -> Optional[Workflow]:
        """
        Retrieve a specific workflow by workflow_id and optional version.
        If version is not provided, returns the stable version.

        Args:
            workflow_id: The workflow identifier.
            version: Optional version number. If None, returns stable version.

        Returns:
            The Workflow instance if found, None otherwise.
        """
        try:
            if version is not None:
                # Get specific version
                result = self.session.execute(
                    text(
                        """
                        SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                        FROM workflows
                        WHERE workflow_id = :workflow_id AND version = :version
                        """
                    ),
                    {"workflow_id": workflow_id, "version": version},
                ).fetchone()
            else:
                # Get stable version
                result = self.session.execute(
                    text(
                        """
                        SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                        FROM workflows
                        WHERE workflow_id = :workflow_id AND stable = true
                        """
                    ),
                    {"workflow_id": workflow_id},
                ).fetchone()

            if result:
                return Workflow(
                    workflow_id=result[0],
                    version=result[1],
                    type=result[2],
                    mermaid=result[3],
                    title=result[4],
                    status=result[5],
                    rationale=result[6],
                    yaml_text=result[7],
                    chat_id=result[8],
                    message_id=result[9],
                    user_id=result[10],
                    model=result[11],
                    stable=result[12],
                    created_at=result[13],
                )
            return None

        except Exception as e:
            logger.error(f"Error retrieving workflow: {e}")
            return None

    def get_workflow_by_message_id(self, message_id: str) -> Optional[Workflow]:
        """
        Retrieve a specific workflow by message_id.

        Args:
            message_id: The message identifier.

        Returns:
            The Workflow instance if found, None otherwise.
        """
        try:
            result = self.session.execute(
                text(
                    """
                    SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                    FROM workflows
                    WHERE message_id = :message_id
                    """
                ),
                {"message_id": message_id},
            ).fetchone()

            if result:
                return Workflow(
                    workflow_id=result[0],
                    version=result[1],
                    type=result[2],
                    mermaid=result[3],
                    title=result[4],
                    status=result[5],
                    rationale=result[6],
                    yaml_text=result[7],
                    chat_id=result[8],
                    message_id=result[9],
                    user_id=result[10],
                    model=result[11],
                    stable=result[12],
                    created_at=result[13],
                )
            return None

        except Exception as e:
            logger.error(f"Error retrieving workflow by message_id: {e}")
            return None

    def get_workflows_by_user_id(
        self, user_id: str, stable_only: bool = True
    ) -> List[Workflow]:
        """
        Retrieve workflows for a specific user.

        Args:
            user_id: The user identifier.
            stable_only: If True, returns only stable versions. If False, returns all versions.

        Returns:
            List of Workflow instances for the user.
        """
        try:
            if stable_only:
                result = self.session.execute(
                    text(
                        """
                        SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at, updated_at
                        FROM workflows
                        WHERE user_id = :user_id AND stable = true
                        ORDER BY created_at DESC
                        """
                    ),
                    {"user_id": user_id},
                ).fetchall()
            else:
                result = self.session.execute(
                    text(
                        """
                        SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at, updated_at
                        FROM workflows
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        """
                    ),
                    {"user_id": user_id},
                ).fetchall()

            workflows = []
            for row in result:
                workflows.append(
                    Workflow(
                        workflow_id=row[0],
                        version=row[1],
                        type=row[2],
                        mermaid=row[3],
                        title=row[4],
                        status=row[5],
                        rationale=row[6],
                        yaml_text=row[7],
                        chat_id=row[8],
                        message_id=row[9],
                        user_id=row[10],
                        model=row[11],
                        stable=row[12],
                        created_at=row[13],
                        updated_at=row[14],
                    )
                )
            return workflows

        except Exception as e:
            logger.error(f"Error retrieving workflows for user {user_id}: {e}")
            return []

    def get_workflows_by_chat_id(self, chat_id: str) -> List[Workflow]:
        """
        Retrieve all workflows for a specific chat session.

        Args:
            chat_id: The chat session identifier.

        Returns:
            List of Workflow instances for the chat session.
        """
        try:
            result = self.session.execute(
                text(
                    """
                    SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                    FROM workflows
                    WHERE chat_id = :chat_id
                    ORDER BY created_at DESC
                    """
                ),
                {"chat_id": chat_id},
            ).fetchall()

            workflows = []
            for row in result:
                workflows.append(
                    Workflow(
                        workflow_id=row[0],
                        version=row[1],
                        type=row[2],
                        mermaid=row[3],
                        rationale=row[4],
                        yaml_text=row[5],
                        chat_id=row[6],
                        message_id=row[7],
                        user_id=row[8],
                        model=row[9],
                        stable=row[10],
                        created_at=row[11],
                    )
                )
            return workflows

        except Exception as e:
            logger.error(f"Error retrieving workflows for chat {chat_id}: {e}")
            return []

    def get_workflows_by_type(
        self, workflow_type: str, stable_only: bool = True
    ) -> List[Workflow]:
        """
        Retrieve all workflows of a specific type.

        Args:
            workflow_type: The workflow type (run-build-flow or run-build-crew).
            stable_only: If True, returns only stable versions. If False, returns all versions.

        Returns:
            List of Workflow instances of the specified type.
        """
        try:
            if stable_only:
                result = self.session.execute(
                    text(
                        """
                        SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                        FROM workflows
                        WHERE type = :workflow_type AND stable = true
                        ORDER BY created_at DESC
                        """
                    ),
                    {"workflow_type": workflow_type},
                ).fetchall()
            else:
                result = self.session.execute(
                    text(
                        """
                        SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                        FROM workflows
                        WHERE type = :workflow_type
                        ORDER BY created_at DESC
                        """
                    ),
                    {"workflow_type": workflow_type},
                ).fetchall()

            workflows = []
            for row in result:
                workflows.append(
                    Workflow(
                        workflow_id=row[0],
                        version=row[1],
                        type=row[2],
                        mermaid=row[3],
                        rationale=row[4],
                        yaml_text=row[5],
                        chat_id=row[6],
                        message_id=row[7],
                        user_id=row[8],
                        model=row[9],
                        stable=row[10],
                        created_at=row[11],
                    )
                )
            return workflows

        except Exception as e:
            logger.error(f"Error retrieving workflows by type {workflow_type}: {e}")
            return []

    def get_workflows_by_message_id(self, message_id: str) -> List[Workflow]:
        """
        Retrieve all workflows associated with a specific message.

        Args:
            message_id: The message identifier.

        Returns:
            List of Workflow instances for the message.
        """
        try:
            result = self.session.execute(
                text(
                    """
                    SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                    FROM workflows
                    WHERE message_id = :message_id
                    ORDER BY created_at DESC
                    """
                ),
                {"message_id": message_id},
            ).fetchall()

            workflows = []
            for row in result:
                workflows.append(
                    Workflow(
                        workflow_id=row[0],
                        version=row[1],
                        type=row[2],
                        mermaid=row[3],
                        rationale=row[4],
                        yaml_text=row[5],
                        chat_id=row[6],
                        message_id=row[7],
                        user_id=row[8],
                        model=row[9],
                        stable=row[10],
                        created_at=row[11],
                    )
                )
            return workflows

        except Exception as e:
            logger.error(f"Error retrieving workflows for message {message_id}: {e}")
            return []

    def update_workflow(
        self, workflow_id: str, version: int, update_data: dict
    ) -> bool:
        """
        Update an existing workflow record.

        Args:
            workflow_id: The workflow identifier.
            version: The version number.
            update_data: Dictionary with fields to update.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            # Build dynamic update query based on provided fields
            set_clauses = []
            params = {"workflow_id": workflow_id, "version": version}

            for field, value in update_data.items():
                if field in [
                    "type",
                    "mermaid",
                    "title",
                    "status",
                    "rationale",
                    "yaml_text",
                    "stable",
                    "model",
                ]:
                    set_clauses.append(f"{field} = :{field}")
                    params[field] = value

            if not set_clauses:
                return False

            query = f"""
                UPDATE workflows
                SET {', '.join(set_clauses)}
                WHERE workflow_id = :workflow_id AND version = :version
            """

            result = self.session.execute(text(query), params)
            self.session.commit()

            return result.rowcount > 0

        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Error updating workflow {workflow_id} version {version}: {e}"
            )
            return False

    def delete_workflow(self, workflow_id: str, version: Optional[int] = None) -> bool:
        """
        Delete a specific workflow or all versions of a workflow.

        Args:
            workflow_id: The workflow identifier.
            version: Optional version number. If None, deletes all versions.

        Returns:
            True if the workflow was deleted, False if not found.
        """
        try:
            if version is not None:
                result = self.session.execute(
                    text(
                        "DELETE FROM workflows WHERE workflow_id = :workflow_id AND version = :version"
                    ),
                    {"workflow_id": workflow_id, "version": version},
                )
            else:
                result = self.session.execute(
                    text("DELETE FROM workflows WHERE workflow_id = :workflow_id"),
                    {"workflow_id": workflow_id},
                )
            self.session.commit()

            return result.rowcount > 0

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting workflow {workflow_id}: {e}")
            return False

    def delete_workflows_by_chat_id(self, chat_id: str) -> int:
        """
        Delete all workflows for a specific chat session.

        Args:
            chat_id: The chat session identifier.

        Returns:
            Number of workflows deleted.
        """
        try:
            result = self.session.execute(
                text("DELETE FROM workflows WHERE chat_id = :chat_id"),
                {"chat_id": chat_id},
            )
            self.session.commit()

            return result.rowcount

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting workflows for chat {chat_id}: {e}")
            return 0

    def get_all_workflows(
        self, limit: Optional[int] = None, stable_only: bool = True
    ) -> List[Workflow]:
        """
        Retrieve all workflows with optional limit.

        Args:
            limit: Optional limit on the number of workflows to retrieve.
            stable_only: If True, returns only stable versions. If False, returns all versions.

        Returns:
            List of Workflow instances.
        """
        try:
            if stable_only:
                query = """
                    SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                    FROM workflows
                    WHERE stable = true
                    ORDER BY created_at DESC
                """
            else:
                query = """
                    SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                    FROM workflows
                    ORDER BY created_at DESC
                """

            if limit:
                query += f" LIMIT {limit}"

            result = self.session.execute(text(query)).fetchall()

            workflows = []
            for row in result:
                workflows.append(
                    Workflow(
                        workflow_id=row[0],
                        version=row[1],
                        type=row[2],
                        mermaid=row[3],
                        rationale=row[4],
                        yaml_text=row[5],
                        chat_id=row[6],
                        message_id=row[7],
                        user_id=row[8],
                        model=row[9],
                        stable=row[10],
                        created_at=row[11],
                    )
                )
            return workflows

        except Exception as e:
            logger.error(f"Error retrieving all workflows: {e}")
            return []

    def get_latest_stable_workflow_by_chat_id(self, chat_id: str) -> Optional[Workflow]:
        """
        Retrieve the latest stable workflow for a specific chat session.

        Args:
            chat_id: The chat session identifier.

        Returns:
            The latest stable Workflow instance for the chat, or None if not found.
        """
        try:
            result = self.session.execute(
                text(
                    """
                    SELECT workflow_id, version, type, mermaid, title, status, rationale, yaml_text, chat_id, message_id, user_id, model, stable, created_at
                    FROM workflows
                    WHERE chat_id = :chat_id AND stable = true
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"chat_id": chat_id},
            ).fetchone()

            if result:
                return Workflow(
                    workflow_id=result[0],
                    version=result[1],
                    type=result[2],
                    mermaid=result[3],
                    title=result[4],
                    status=result[5],
                    rationale=result[6],
                    yaml_text=result[7],
                    chat_id=result[8],
                    message_id=result[9],
                    user_id=result[10],
                    model=result[11],
                    stable=result[12],
                    created_at=result[13],
                )
            return None

        except Exception as e:
            logger.error(
                f"Error retrieving latest stable workflow for chat {chat_id}: {e}"
            )
            return None

    def get_chat_context_for_generation(
        self, chat_id: str
    ) -> tuple[Optional[Workflow], Optional[str]]:
        """
        Get complete chat context (latest stable workflow + conversation summary) in a single optimized query.

        Args:
            chat_id: The chat session identifier.

        Returns:
            Tuple of (latest_stable_workflow, conversation_summary)
        """
        try:
            result = self.session.execute(
                text(
                    """
                    WITH latest_workflow AS (
                        SELECT w.workflow_id, w.version, w.type, w.mermaid, w.rationale, w.yaml_text,
                               w.chat_id, w.message_id, w.user_id, w.stable, w.created_at
                        FROM workflows w
                        WHERE w.chat_id = :chat_id AND w.stable = true
                        ORDER BY w.created_at DESC
                        LIMIT 1
                    ),
                    latest_summary AS (
                        SELECT cm.summary
                        FROM chat_messages cm
                        WHERE cm.chat_id = :chat_id AND cm.summary IS NOT NULL
                        ORDER BY cm.created_at DESC
                        LIMIT 1
                    )
                    SELECT
                        lw.workflow_id, lw.version, lw.type, lw.mermaid, lw.rationale, lw.yaml_text,
                        lw.chat_id, lw.message_id, lw.user_id, lw.stable, lw.created_at,
                        ls.summary
                    FROM latest_workflow lw
                    FULL OUTER JOIN latest_summary ls ON true
                """
                ),
                {"chat_id": chat_id},
            ).fetchone()

            if not result:
                return None, None

            # Check if we have workflow data (not all NULL)
            if result[0] is not None:  # workflow_id is not NULL
                workflow = Workflow(
                    workflow_id=result[0],
                    version=result[1],
                    type=result[2],
                    mermaid=result[3],
                    rationale=result[4],
                    yaml_text=result[5],
                    chat_id=result[6],
                    message_id=result[7],
                    user_id=result[8],
                    model=result[9],
                    stable=result[10],
                    created_at=result[11],
                )
            else:
                workflow = None

            summary = result[11] if result[11] else None

            return workflow, summary

        except Exception as e:
            logger.error(f"Error retrieving chat context for chat {chat_id}: {e}")
            return None, None

    def get_next_version_number(self, workflow_id: str) -> int:
        """
        Get the next version number for a workflow.

        Args:
            workflow_id: The workflow identifier.

        Returns:
            The next version number (1 if no previous versions exist).
        """
        try:
            result = self.session.execute(
                text(
                    """
                    SELECT MAX(version) as max_version
                    FROM workflows
                    WHERE workflow_id = :workflow_id
                    """
                ),
                {"workflow_id": workflow_id},
            ).fetchone()

            if result and result[0] is not None:
                return result[0] + 1
            return 1

        except Exception as e:
            logger.error(f"Error getting next version for workflow {workflow_id}: {e}")
            return 1

    def check_title_exists_for_user(
        self, title: str, user_id: str, exclude_workflow_id: Optional[str] = None
    ) -> bool:
        """
        Check if a workflow with the given title exists for the user.

        Args:
            title: The workflow title to check.
            user_id: The user identifier.
            exclude_workflow_id: Optional workflow_id to exclude from the check (for versioning).

        Returns:
            True if a workflow with this title exists for the user, False otherwise.
        """
        if not title or not user_id:
            return False

        try:
            if exclude_workflow_id:
                result = self.session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM workflows
                        WHERE title = :title
                        AND user_id = :user_id
                        AND workflow_id != :exclude_workflow_id
                        AND stable = true
                        """
                    ),
                    {
                        "title": title,
                        "user_id": user_id,
                        "exclude_workflow_id": exclude_workflow_id,
                    },
                ).fetchone()
            else:
                result = self.session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM workflows
                        WHERE title = :title
                        AND user_id = :user_id
                        AND stable = true
                        """
                    ),
                    {"title": title, "user_id": user_id},
                ).fetchone()

            return result[0] > 0 if result else False

        except Exception as e:
            logger.error(f"Error checking title existence for user {user_id}: {e}")
            return False

    def mark_previous_versions_unstable(self, workflow_id: str) -> bool:
        """
        Mark all previous versions of a workflow as unstable.

        Args:
            workflow_id: The workflow identifier.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            result = self.session.execute(
                text(
                    """
                    UPDATE workflows
                    SET stable = false
                    WHERE workflow_id = :workflow_id
                    """
                ),
                {"workflow_id": workflow_id},
            )
            self.session.commit()
            return result.rowcount >= 0

        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Error marking previous versions unstable for workflow {workflow_id}: {e}"
            )
            return False
