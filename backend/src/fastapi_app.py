from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.db import get_db, get_new_db_session
from lite_llm_handler import get_llm
from example_crew import run_crew

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="BlendX CrewAI API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class CrewStartResponse(BaseModel):
    execution_id: str
    status: str
    message: str


class CrewStatusResponse(BaseModel):
    execution_id: str
    status: str
    result: dict | None = None
    error: str | None = None


# Background task function
async def run_crew_background(execution_id: str):
    """
    Background task que ejecuta la crew y guarda el resultado en la BD.
    """
    logger.info(f"Starting crew execution for ID: {execution_id}")

    try:
        with get_new_db_session() as session:
            # Get LLM
            llm = get_llm(provider='snowflake', model='claude-3-5-sonnet')
            logger.info(f"LLM initialized for execution {execution_id}")

            # Run Crew
            logger.info(f"Running crew for execution {execution_id}")
            crew_output = run_crew(llm)
            logger.info(f"Crew execution completed for {execution_id}")

            # Prepare data for saving
            result_text = None
            raw_output = None

            if hasattr(crew_output, 'json_dict') and crew_output.json_dict:
                raw_output = crew_output.json_dict
                result_text = str(crew_output.json_dict)
            elif hasattr(crew_output, 'raw'):
                result_text = crew_output.raw
                raw_output = {"raw": crew_output.raw}
            else:
                result_text = str(crew_output)
                raw_output = {"output": result_text}

            table_name = "spcs_app_instance_test.app_data.crew_execution_results"

            # Prepare JSON strings
            raw_output_json = json.dumps(raw_output)
            metadata_json = json.dumps({
                "model": "claude-3-5-sonnet",
                "provider": "snowflake",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Update record with SUCCESS status
            update_query = text(f"""
                UPDATE {table_name}
                SET
                    raw_output = PARSE_JSON(:raw_output),
                    result_text = :result_text,
                    status = :status,
                    metadata = PARSE_JSON(:metadata),
                    updated_at = CURRENT_TIMESTAMP()
                WHERE id = :id
            """)

            session.execute(update_query, {
                "id": execution_id,
                "raw_output": raw_output_json,
                "result_text": result_text,
                "status": "COMPLETED",
                "metadata": metadata_json
            })
            session.commit()

            logger.info(f"Crew result saved successfully for {execution_id}")

    except Exception as e:
        logger.error(f"Error in crew execution {execution_id}: {str(e)}", exc_info=True)

        # Update record with ERROR status
        try:
            with get_new_db_session() as session:
                table_name = "spcs_app_instance_test.app_data.crew_execution_results"
                error_query = text(f"""
                    UPDATE {table_name}
                    SET
                        status = :status,
                        result_text = :error_message,
                        updated_at = CURRENT_TIMESTAMP()
                    WHERE id = :id
                """)

                session.execute(error_query, {
                    "id": execution_id,
                    "status": "ERROR",
                    "error_message": str(e)
                })
                session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status for {execution_id}: {str(db_error)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "BlendX CrewAI API"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    import os
    health_info = {
        'status': 'ok',
        'environment': os.getenv('ENVIRONMENT', 'not set'),
        'snowflake_authmethod': os.getenv('SNOWFLAKE_AUTHMETHOD', 'not set'),
        'snowflake_account': os.getenv('SNOWFLAKE_ACCOUNT', 'not set'),
        'oauth_token_exists': os.path.exists('/snowflake/session/token')
    }

    if health_info['oauth_token_exists']:
        try:
            with open('/snowflake/session/token', 'r') as f:
                token = f.read().strip()
                health_info['oauth_token_length'] = len(token)
        except Exception as e:
            health_info['oauth_token_error'] = str(e)

    return health_info


@app.post("/crew/start", response_model=CrewStartResponse)
async def start_crew_execution(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Inicia la ejecución de la crew en background.

    Steps:
    1. Genera un UUID único
    2. Crea un registro en la BD con status='PROCESSING'
    3. Lanza la tarea en background
    4. Retorna el ID inmediatamente
    """
    try:
        # 1. Generate unique ID
        execution_id = str(uuid.uuid4())
        logger.info(f"Starting new crew execution with ID: {execution_id}")

        # 2. Create initial record in database with PROCESSING status
        table_name = "spcs_app_instance_test.app_data.crew_execution_results"

        metadata_json = json.dumps({
            "model": "claude-3-5-sonnet",
            "provider": "snowflake",
            "started_at": datetime.now(timezone.utc).isoformat()
        })

        insert_query = text(f"""
            INSERT INTO {table_name}
            (id, crew_name, status, metadata, result_text)
            SELECT
                :id,
                :crew_name,
                :status,
                PARSE_JSON(:metadata),
                :result_text
        """)

        db.execute(insert_query, {
            "id": execution_id,
            "crew_name": "YourCrewName",
            "status": "PROCESSING",
            "metadata": metadata_json,
            "result_text": "Processing..."
        })
        db.commit()

        logger.info(f"Initial record created for {execution_id}")

        # 3. Add background task
        background_tasks.add_task(run_crew_background, execution_id)

        # 4. Return ID immediately
        return CrewStartResponse(
            execution_id=execution_id,
            status="PROCESSING",
            message="Crew execution started successfully"
        )

    except Exception as e:
        logger.error(f"Error starting crew execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start crew execution: {str(e)}")


@app.get("/crew/status/{execution_id}", response_model=CrewStatusResponse)
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
        table_name = "spcs_app_instance_test.app_data.crew_execution_results"

        query = text(f"""
            SELECT
                id,
                status,
                raw_output,
                result_text,
                metadata
            FROM {table_name}
            WHERE id = :execution_id
        """)

        result = db.execute(query, {"execution_id": execution_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"Execution ID {execution_id} not found")

        row_id, status, raw_output, result_text, metadata = result

        if status == "PROCESSING":
            return CrewStatusResponse(
                execution_id=row_id,
                status="PROCESSING",
                result=None,
                error=None
            )
        elif status == "COMPLETED":
            # Parse raw_output if it's a JSON string
            try:
                result_data = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            except:
                result_data = {"raw": str(raw_output)}

            return CrewStatusResponse(
                execution_id=row_id,
                status="COMPLETED",
                result=result_data,
                error=None
            )
        elif status == "ERROR":
            return CrewStatusResponse(
                execution_id=row_id,
                status="ERROR",
                result=None,
                error=result_text
            )
        else:
            # Unknown status
            return CrewStatusResponse(
                execution_id=row_id,
                status=status,
                result={"raw": result_text} if result_text else None,
                error=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving crew status for {execution_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve status: {str(e)}")


@app.get("/crew/executions")
async def list_crew_executions(limit: int = 10, db: Session = Depends(get_db)):
    """
    Lista las últimas ejecuciones de crew (útil para debugging).
    """
    try:
        table_name = "spcs_app_instance_test.app_data.crew_execution_results"

        query = text(f"""
            SELECT
                id,
                crew_name,
                status,
                execution_timestamp,
                updated_at
            FROM {table_name}
            ORDER BY execution_timestamp DESC
            LIMIT :limit
        """)

        results = db.execute(query, {"limit": limit}).fetchall()

        executions = []
        for row in results:
            executions.append({
                "execution_id": row[0],
                "crew_name": row[1],
                "status": row[2],
                "execution_timestamp": str(row[3]) if row[3] else None,
                "updated_at": str(row[4]) if row[4] else None
            })

        return {"executions": executions}

    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os
    api_port = int(os.getenv('API_PORT') or 8081)
    logger.info(f"Starting FastAPI app on port {api_port}")
    uvicorn.run(app, host="0.0.0.0", port=api_port)
