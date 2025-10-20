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
from workflows import CompanySearchWorkflow, CompanyDetailWorkflow


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

# Store company lists for each session (for selection)
session_company_lists: Dict[str, List[Dict[str, Any]]] = {}

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

    Handles two modes:
    1. Company name search - returns numbered list of matching companies
    2. Number selection - returns detailed JSON info for selected company

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
        session_company_lists[session_id] = []

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
        # Check if query is a number (selection mode)
        query_stripped = request.query.strip()
        is_number_selection = query_stripped.isdigit()

        if is_number_selection:
            # Mode 2: User selected a number from the list
            selection_number = int(query_stripped)

            # Validate selection
            if session_id not in session_company_lists or not session_company_lists[session_id]:
                raise HTTPException(
                    status_code=400,
                    detail="No company list found. Please search for companies first."
                )

            company_list = session_company_lists[session_id]
            if selection_number < 1 or selection_number > len(company_list):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid selection. Please choose a number between 1 and {len(company_list)}."
                )

            # Get selected company (1-indexed)
            selected_company = company_list[selection_number - 1]
            company_name = selected_company.get("name")
            company_website = selected_company.get("website")

            logger.info(f"User selected company #{selection_number}: {company_name}")

            # Execute detailed company info workflow
            workflow_id = f"company-detail-{message_id}"
            logger.info(f"Starting detail workflow {workflow_id} for: {company_name}")

            result = await temporal_client.execute_workflow(
                CompanyDetailWorkflow.run,
                args=[company_name, company_website],
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
            )

            logger.info(f"Detail workflow completed: {workflow_id}")

            # Format the detailed info response
            detailed_data = result.get("detailed_info", {}).get("data", {})

            response_content = {
                "mode": "detailed_info",
                "company_number": selection_number,
                "data": detailed_data
            }

        else:
            # Mode 1: User entered a company name - search and list companies
            workflow_id = f"company-search-{message_id}"
            logger.info(f"Starting search workflow {workflow_id} for query: {request.query}")

            result = await temporal_client.execute_workflow(
                CompanySearchWorkflow.run,
                request.query,
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
            )

            logger.info(f"Search workflow completed: {workflow_id}")

            # Extract and number the companies
            search_results = result.get("search_results", {})
            companies = search_results.get("results", [])

            if isinstance(companies, list) and len(companies) > 0:
                # Store the company list for this session
                session_company_lists[session_id] = companies

                # Create numbered list response
                numbered_companies = []
                for idx, company in enumerate(companies, start=1):
                    numbered_company = {
                        "number": idx,
                        **company
                    }
                    numbered_companies.append(numbered_company)

                response_content = {
                    "mode": "company_list",
                    "count": len(numbered_companies),
                    "companies": numbered_companies,
                    "message": f"Found {len(numbered_companies)} companies. Please enter a number to get detailed information."
                }
            else:
                response_content = {
                    "mode": "company_list",
                    "count": 0,
                    "companies": [],
                    "message": "No companies found matching your search.",
                    "raw_result": result
                }

        # Add assistant response to session
        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        chat_sessions[session_id].append(assistant_message)

        return SearchResponse(
            session_id=session_id,
            message_id=message_id,
            query=request.query,
            results=response_content
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
