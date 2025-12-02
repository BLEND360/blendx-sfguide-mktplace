"""
BlendX CrewAI API - Main Application.

FastAPI application with modular router structure.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import crew_router, health_router, nl_ai_generator_router, nl_ai_generator_async_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="BlendX CrewAI API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router.router)
app.include_router(crew_router.router)
app.include_router(nl_ai_generator_router.router)
app.include_router(nl_ai_generator_async_router.router)


if __name__ == "__main__":
    import uvicorn

    api_port = int(os.getenv("API_PORT") or 8081)
    logger.info(f"Starting FastAPI app on port {api_port}")
    uvicorn.run(app, host="0.0.0.0", port=api_port)
