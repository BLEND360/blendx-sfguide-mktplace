from http.client import HTTPException
from flask import Blueprint, request, abort, make_response, jsonify

import datetime
import logging
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

            # Get current session info for debugging
            try:
                current_user = session.execute(text("SELECT CURRENT_USER()")).fetchone()[0]
                current_role = session.execute(text("SELECT CURRENT_ROLE()")).fetchone()[0]
                current_warehouse = session.execute(text("SELECT CURRENT_WAREHOUSE()")).fetchone()[0]
                logger.info(f"Session info - User: {current_user}, Role: {current_role}, Warehouse: {current_warehouse}")
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
                llm = get_llm(provider='snowflake', model='mistral-large')
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

            except Exception as e:
                logger.error(f"Failed to create LLM: {str(e)}", exc_info=True)
                return make_response(jsonify({"error": str(e)}), 500)

            return make_response(jsonify({"response": response}))

    except Exception as ex:
        logger.error(f"ERROR in llm_call endpoint: {str(ex)}", exc_info=True)
        abort(500, f"Error calling LLM: {str(ex)}")
        


    