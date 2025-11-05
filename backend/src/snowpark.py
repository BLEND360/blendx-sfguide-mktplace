from flask import Blueprint, request, abort, make_response, jsonify
import datetime
from sqlalchemy import text

from database.db import get_new_db_session

# Make the API endpoints
snowpark = Blueprint('snowpark', __name__)

dateformat = '%Y-%m-%d'

## Top clerks in date range
@snowpark.route('/top_clerks')
def top_clerks():
    # Validate arguments
    sdt_str = request.args.get('start_range') or '1995-01-01'
    edt_str = request.args.get('end_range') or '1995-03-31'
    topn_str = request.args.get('topn') or '10'
    try:
        sdt = datetime.datetime.strptime(sdt_str, dateformat)
        edt = datetime.datetime.strptime(edt_str, dateformat)
        topn = int(topn_str)
    except:
        abort(400, "Invalid arguments.")
    with get_new_db_session() as session:
        try:
            sql = text("""
                SELECT O_CLERK, SUM(O_TOTALPRICE) as CLERK_TOTAL
                FROM NAC_TEST_DB.DATA.ORDERS
                WHERE O_ORDERDATE >= :start_date
                  AND O_ORDERDATE <= :end_date
                GROUP BY O_CLERK
                ORDER BY CLERK_TOTAL DESC
                LIMIT :limit
            """)
            result = session.execute(sql, {
                'start_date': sdt,
                'end_date': edt,
                'limit': topn
            })
            rows = [dict(row._mapping) for row in result]
            return make_response(jsonify(rows))
        except Exception as ex:
            print(f"ERROR: {ex}")
            abort(500, "Error reading from Snowflake. Check the logs for details.")

@snowpark.route('/llm-call')
def llm_call():
    try:
        with get_new_db_session() as session:
            a = session.execute(text("SELECT 1"))
            print('DB Connection OK')
            result = session.execute(text("""SELECT AI_COMPLETE('SNOWFLAKE.MODELS."LLAMA3.1-70B"', 'Hello');"""))
            response = result.fetchone()[0]
            print(f"Call LLM, response:{response}")
            return make_response(jsonify({"response": response}))

    except Exception as ex:
        print(f"ERROR while connecting to DB {ex}")
        abort(500, f"Error calling LLM: {str(ex)}")
        