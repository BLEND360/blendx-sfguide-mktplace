from flask import Flask, jsonify, make_response
from flask_cors import CORS
import os
import logging
import traceback
from snowpark import snowpark

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.register_blueprint(snowpark, url_prefix='/snowpark')

@app.route("/")
def default():
    return make_response(jsonify(result='Nothing to see here'))

@app.route("/health")
def health():
    """Health check endpoint"""
    import os
    health_info = {
        'status': 'ok',
        'environment': os.getenv('ENVIRONMENT', 'not set'),
        'snowflake_authmethod': os.getenv('SNOWFLAKE_AUTHMETHOD', 'not set'),
        'snowflake_account': os.getenv('SNOWFLAKE_ACCOUNT', 'not set'),
        'oauth_token_exists': os.path.exists('/snowflake/session/token')
    }

    # Try to read token if it exists
    if health_info['oauth_token_exists']:
        try:
            with open('/snowflake/session/token', 'r') as f:
                token = f.read().strip()
                health_info['oauth_token_length'] = len(token)
        except Exception as e:
            health_info['oauth_token_error'] = str(e)

    return make_response(jsonify(health_info))

@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    logger.error(traceback.format_exc())
    return make_response(jsonify(error='Internal server error', details=str(e)), 500)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    return make_response(jsonify(error='Internal server error', details=str(e)), 500)

if __name__ == '__main__':
    api_port=int(os.getenv('API_PORT') or 8081)
    logger.info(f"Starting Flask app on port {api_port}")
    app.run(port=api_port, host='0.0.0.0')
