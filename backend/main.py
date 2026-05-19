"""FastAPI application for the Resume Assistant."""

import logging
import sys
from logging import LogLevel

from fastapi import FastAPI

from api import chat_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("truresume")

app = FastAPI(
    title="TRUResume HIRE API",
    description="Resume Assistant chatbot API using LangGraph and Groq",
    version="0.1.0",
)

app.include_router(chat_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check requested")
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("TRUResume HIRE API starting up...")
    logger.info("Endpoints: POST /chat/, POST /chat/stream, POST /chat/resume/upload, GET /health")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("TRUResume HIRE API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, loop="auto")