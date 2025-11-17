from http.client import HTTPException
from flask import Blueprint, abort, make_response, jsonify

import logging
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import text

from database.db import get_new_db_session
from lite_llm_handler import get_llm
from example_crew import run_crew

# Make the API endpoints
snowpark = Blueprint('snowpark', __name__)
logger = logging.getLogger(__name__)

@snowpark.route('/llm-call')
def llm_call():
    try:
        with get_new_db_session() as session:
            # Test DB connection
            session.execute(text("SELECT 1"))
            logger.info('DB Connection - OK')

            try:
                current_user = session.execute(text("SELECT CURRENT_USER()")).fetchone()[0]
                current_role = session.execute(text("SELECT CURRENT_ROLE()")).fetchone()[0]
                current_warehouse = session.execute(text("SELECT CURRENT_WAREHOUSE()")).fetchone()[0]

                logger.info(f"User: {current_user}, Role: {current_role}, Warehouse: {current_warehouse}")
            except Exception as info_ex:
                logger.warning(f"Could not get session info: {info_ex}")

            # Try to call LLM
            llm_query = "SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-8b', 'hello')"
            logger.info(f"Executing LLM query: {llm_query}")

            result = session.execute(text(llm_query))
            response = result.fetchone()[0]
            logger.info(f"LLM call successful. Response: {response}")

            # Try to use LiteLLM handler
            try:
                llm = get_llm(provider='snowflake', model='claude-3-5-sonnet')
                logger.info("Calling LLM..")
                response = llm.call([({"role": "user", "content": "Hello"})])
                logger.info(f"Get response from LLM {response}")

                # Run Crew
                logger.info("Running Crew")
                crew_output = run_crew(llm)
                logging.info("FINISH")

                # Convert CrewOutput to JSON-serializable format
                if hasattr(crew_output, 'json_dict') and crew_output.json_dict:
                    response = crew_output.json_dict
                elif hasattr(crew_output, 'raw'):
                    response = crew_output.raw
                else:
                    response = str(crew_output)

                # Save crew results to database
                try:
                    execution_id = str(uuid.uuid4())

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


                    table_name = f"spcs_app_instance_test.app_data.crew_execution_results"

                    # Prepare JSON strings for insertion
                    raw_output_json = json.dumps(raw_output)
                    metadata_json = json.dumps({
                        "model": "claude-3-5-sonnet",
                        "provider": "snowflake",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    # Insert into database using TO_VARIANT instead of PARSE_JSON for better compatibility
                    insert_query = text(f"""
                        INSERT INTO {table_name}
                        (id, crew_name, raw_output, result_text, status, metadata)
                        SELECT
                            :id,
                            :crew_name,
                            PARSE_JSON(:raw_output),
                            :result_text,
                            :status,
                            PARSE_JSON(:metadata)
                    """)

                    session.execute(insert_query, {
                        "id": execution_id,
                        "crew_name": "YourCrewName",
                        "raw_output": raw_output_json,
                        "result_text": result_text,
                        "status": "SUCCESS",
                        "metadata": metadata_json
                    })
                    session.commit()

                    logger.info(f"Crew result saved to database with ID: {execution_id}")

                except Exception as db_error:
                    logger.error(f"Failed to save crew result to database: {str(db_error)}", exc_info=True)
                    # Don't fail the request if saving fails
                    session.rollback()

            except Exception as e:
                logger.error(f"Failed to create LLM: {str(e)}", exc_info=True)
                return make_response(jsonify({"error": str(e)}), 500)

            return make_response(jsonify({"response": response}))

    except Exception as ex:
        logger.error(f"ERROR in llm_call endpoint: {str(ex)}", exc_info=True)
        abort(500, f"Error calling LLM: {str(ex)}")
        