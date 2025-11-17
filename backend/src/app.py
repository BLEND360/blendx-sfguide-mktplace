# This file now imports and runs the FastAPI application
# The old Flask app has been replaced with FastAPI for better async support
from fastapi_app import app

if __name__ == '__main__':
    import uvicorn
    import os
    api_port = int(os.getenv('API_PORT') or 8081)
    uvicorn.run(app, host="0.0.0.0", port=api_port)
