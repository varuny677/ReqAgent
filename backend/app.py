"""
FastAPI server for the company search application.

This module provides REST API endpoints and manages Temporal workflow execution.
"""

import logging
import uuid
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

from config import settings
from workflows import CompanySearchWorkflow


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Company Search API",
    description="API for searching companies using Google ADK and Gemini",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store chat sessions in memory (session-based)
chat_sessions: Dict[str, List[Dict[str, Any]]] = {}

# Temporal client (will be initialized on startup)
temporal_client: Client = None


class SearchRequest(BaseModel):
    """Request model for company search."""

    query: str
    session_id: str = None


class SearchResponse(BaseModel):
    """Response model for company search."""

    session_id: str
    message_id: str
    query: str
    results: Dict[str, Any]


class ChatMessage(BaseModel):
    """Chat message model."""

    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class SessionResponse(BaseModel):
    """Session response model."""

    session_id: str
    messages: List[Dict[str, Any]]


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize Temporal client on startup."""
    global temporal_client
    logger.info(f"Connecting to Temporal at {settings.temporal_host}")
    try:
        temporal_client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
        logger.info("Successfully connected to Temporal server")
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {str(e)}")
        logger.warning("Server will start but search functionality may not work")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Company Search API",
        "status": "running"
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    temporal_status = "connected" if temporal_client else "disconnected"
    return {
        "status": "healthy",
        "temporal": temporal_status
    }


@app.post("/api/search", response_model=SearchResponse)
async def search_companies(request: SearchRequest) -> SearchResponse:
    """
    Search for companies using Temporal workflow.

    Args:
        request: Search request containing query and optional session_id

    Returns:
        Search response with results
    """
    if not temporal_client:
        raise HTTPException(
            status_code=503,
            detail="Temporal client not connected. Please ensure Temporal server is running."
        )

    # Generate or use existing session ID
    session_id = request.session_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    # Initialize session if new
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # Add user message to session
    import datetime
    user_message = {
        "id": message_id,
        "role": "user",
        "content": request.query,
        "timestamp": datetime.datetime.now().isoformat()
    }
    chat_sessions[session_id].append(user_message)

    try:
        # Execute Temporal workflow
        workflow_id = f"company-search-{message_id}"
        logger.info(f"Starting workflow {workflow_id} for query: {request.query}")

        result = await temporal_client.execute_workflow(
            CompanySearchWorkflow.run,
            request.query,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        logger.info(f"Workflow completed: {workflow_id}")

        # Add assistant response to session
        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": result,
            "timestamp": datetime.datetime.now().isoformat()
        }
        chat_sessions[session_id].append(assistant_message)

        return SearchResponse(
            session_id=session_id,
            message_id=message_id,
            query=request.query,
            results=result
        )

    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching companies: {str(e)}"
        )


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """
    Get chat session by ID.

    Args:
        session_id: Session identifier

    Returns:
        Session with all messages
    """
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session_id,
        messages=chat_sessions[session_id]
    )


@app.get("/api/sessions")
async def list_sessions() -> Dict[str, List[str]]:
    """
    List all active sessions.

    Returns:
        List of session IDs
    """
    return {"sessions": list(chat_sessions.keys())}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    Delete a chat session.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info"
    )
