"""
FastAPI server for the company search application.

This module provides REST API endpoints and manages Temporal workflow execution.
"""

import logging
import uuid
import os
import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

from config import settings
from workflows import CompanySearchWorkflow, CompanyDetailWorkflow
from services import FirestoreService
from activities import infer_presumptive_config


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

# Temporal client (will be initialized on startup)
temporal_client: Client = None

# Firestore service (will be initialized on startup)
firestore_service: FirestoreService = None


class SearchRequest(BaseModel):
    """Request model for company search."""

    query: str
    session_id: Optional[str] = None


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


class ConfigRequest(BaseModel):
    """Request model for generating presumptive configuration."""

    company_data: Dict[str, Any]


class ConfigSaveRequest(BaseModel):
    """Request model for saving configuration."""

    session_id: str
    configuration: Dict[str, Any]


class ConfigResponse(BaseModel):
    """Response model for configuration."""

    success: bool
    data: Dict[str, Any]
    session_id: Optional[str] = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize Temporal client and Firestore on startup."""
    global temporal_client, firestore_service

    # Initialize Temporal
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

    # Initialize Firestore
    logger.info("Initializing Firestore service")
    try:
        credentials_path = os.path.join(
            os.path.dirname(__file__), "reqagent-c12e92ab61f5.json"
        )
        firestore_service = FirestoreService(
            credentials_path=credentials_path,
            database_name="reqdb"
        )
        logger.info("Successfully initialized Firestore service")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {str(e)}")
        logger.warning("Server will start but persistence may not work")


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
    firestore_status = "connected" if firestore_service else "disconnected"
    return {
        "status": "healthy",
        "temporal": temporal_status,
        "firestore": firestore_status
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
    logger.info(f"Received search request: query={request.query}, session_id={request.session_id}")

    if not temporal_client:
        raise HTTPException(
            status_code=503,
            detail="Temporal client not connected. Please ensure Temporal server is running."
        )

    if not firestore_service:
        raise HTTPException(
            status_code=503,
            detail="Firestore service not initialized."
        )

    # Generate or use existing session ID
    session_id = request.session_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    # Initialize session if new
    session = firestore_service.get_session(session_id)
    if not session:
        # Create new session with first query as title
        title = request.query[:30] + ("..." if len(request.query) > 30 else "")
        session = firestore_service.create_session(
            session_id=session_id,
            title=title,
            preview=request.query
        )
        logger.info(f"Created new session: {session_id}")

    # Add user message to Firestore
    user_message_timestamp = datetime.datetime.now()
    firestore_service.add_message(
        session_id=session_id,
        message_id=message_id,
        role="user",
        content=request.query,
        timestamp=user_message_timestamp
    )

    try:
        # Check if query is a number (selection mode)
        query_stripped = request.query.strip()
        is_number_selection = query_stripped.isdigit()

        if is_number_selection:
            # Mode 2: User selected a number from the list
            selection_number = int(query_stripped)

            # Get company list from Firestore
            company_list = firestore_service.get_company_list(session_id)

            # Validate selection
            if not company_list:
                raise HTTPException(
                    status_code=400,
                    detail="No company list found. Please search for companies first."
                )
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

            # Generate presumptive configuration using AI
            logger.info("Generating presumptive configuration from company data")
            try:
                config_result = await infer_presumptive_config(detailed_data)
                presumptive_config = config_result.get("data", {})
                logger.info("Presumptive config generated successfully")
            except Exception as e:
                logger.error(f"Error generating config: {str(e)}")
                # Use defaults if AI fails
                presumptive_config = {
                    "industry_sector": "Technology & Software",
                    "sub_sector": "Enterprise Software",
                    "cloud_provider": "AWS",
                    "target_continent": "North America",
                    "region_strategy": "Single Region"
                }

            response_content = {
                "mode": "detailed_info",
                "company_number": selection_number,
                "data": detailed_data,
                "presumptive_config": presumptive_config,
                "show_form": True  # Trigger form display in frontend
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
                # Store the company list in Firestore
                firestore_service.set_company_list(session_id, companies)

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

        # Add assistant response to Firestore
        assistant_message_id = str(uuid.uuid4())
        assistant_message_timestamp = datetime.datetime.now()
        firestore_service.add_message(
            session_id=session_id,
            message_id=assistant_message_id,
            role="assistant",
            content=response_content,
            timestamp=assistant_message_timestamp
        )

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


@app.get("/api/sessions")
async def list_sessions() -> Dict[str, Any]:
    """
    List all active sessions (last 20, ordered by most recent).

    Returns:
        Dictionary with list of sessions
    """
    if not firestore_service:
        raise HTTPException(
            status_code=503,
            detail="Firestore service not initialized."
        )

    try:
        sessions = firestore_service.list_sessions(limit=20)

        # Convert datetime objects to ISO format strings for JSON serialization
        for session in sessions:
            if "created_at" in session and session["created_at"]:
                try:
                    session["created_at"] = session["created_at"].isoformat()
                except Exception:
                    session["created_at"] = None
            if "updated_at" in session and session["updated_at"]:
                try:
                    session["updated_at"] = session["updated_at"].isoformat()
                except Exception:
                    session["updated_at"] = None

        return {"sessions": sessions}

    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error listing sessions: {str(e)}"
        )


@app.get("/api/sessions/{session_id}")
async def get_session_with_messages(session_id: str) -> Dict[str, Any]:
    """
    Get session by ID with all messages.

    Args:
        session_id: Session identifier

    Returns:
        Session data with messages
    """
    if not firestore_service:
        raise HTTPException(
            status_code=503,
            detail="Firestore service not initialized."
        )

    try:
        data = firestore_service.get_session_with_messages(session_id)

        if not data:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert datetime objects to ISO format strings
        session = data["session"]
        if "created_at" in session and session["created_at"]:
            session["created_at"] = session["created_at"].isoformat()
        if "updated_at" in session and session["updated_at"]:
            session["updated_at"] = session["updated_at"].isoformat()

        for message in data["messages"]:
            if "timestamp" in message and message["timestamp"]:
                message["timestamp"] = message["timestamp"].isoformat()

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting session: {str(e)}"
        )


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    Delete a chat session and all its messages.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    if not firestore_service:
        raise HTTPException(
            status_code=503,
            detail="Firestore service not initialized."
        )

    try:
        # Check if session exists
        session = firestore_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete session and all messages
        firestore_service.delete_session(session_id)

        return {"message": f"Session {session_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting session: {str(e)}"
        )


@app.post("/api/generate-config", response_model=ConfigResponse)
async def generate_presumptive_config(request: ConfigRequest) -> ConfigResponse:
    """
    Generate presumptive configuration form values from company data using AI.

    This endpoint uses Temporal activity to call Gemini AI for intelligent
    inference of configuration values based on company information.

    Args:
        request: Contains company_data dictionary

    Returns:
        ConfigResponse with inferred configuration values
    """
    logger.info("Received request to generate presumptive config")

    try:
        # Execute the infer activity directly (not through workflow)
        # We can call activities directly for simple operations
        result = await infer_presumptive_config(request.company_data)

        if result.get("success"):
            logger.info("Successfully generated presumptive config")
            return ConfigResponse(
                success=True,
                data=result.get("data", {})
            )
        else:
            logger.warning(f"Config generation had issues: {result.get('error')}")
            # Still return the default values provided in the result
            return ConfigResponse(
                success=False,
                data=result.get("data", {})
            )

    except Exception as e:
        logger.error(f"Error generating config: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error generating config: {str(e)}"
        )


@app.post("/api/save-config", response_model=ConfigResponse)
async def save_configuration(request: ConfigSaveRequest) -> ConfigResponse:
    """
    Save user's configuration selections to Firestore.

    Args:
        request: Contains session_id and configuration data

    Returns:
        ConfigResponse confirming save operation
    """
    logger.info(
        f"Received request to save config for session: {request.session_id}"
    )

    if not firestore_service:
        raise HTTPException(
            status_code=503,
            detail="Firestore service not initialized."
        )

    try:
        # Validate session exists
        session = firestore_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Save configuration
        saved_config = firestore_service.save_configuration(
            request.session_id,
            request.configuration
        )

        logger.info(f"Successfully saved config for session: {request.session_id}")

        return ConfigResponse(
            success=True,
            data=saved_config,
            session_id=request.session_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error saving config: {str(e)}"
        )


@app.get("/api/sessions/{session_id}/config")
async def get_session_config(session_id: str) -> Dict[str, Any]:
    """
    Get saved configuration for a session.

    Args:
        session_id: Session identifier

    Returns:
        Configuration data or empty dict if not found
    """
    if not firestore_service:
        raise HTTPException(
            status_code=503,
            detail="Firestore service not initialized."
        )

    try:
        config = firestore_service.get_configuration(session_id)

        if config:
            return {"configuration": config}
        else:
            return {"configuration": None}

    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting config: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info"
    )
