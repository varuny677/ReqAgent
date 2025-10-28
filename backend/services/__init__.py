"""Services package for backend."""

from .firestore_service import FirestoreService
from .rag_client import RAGClient, get_rag_client
from .rag_filter import RAGFilter, get_rag_filter, should_question_use_rag
from .prediction_context import (
    PredictionContext,
    get_or_create_context,
    clear_context,
    get_active_sessions
)

__all__ = [
    "FirestoreService",
    "RAGClient",
    "get_rag_client",
    "RAGFilter",
    "get_rag_filter",
    "should_question_use_rag",
    "PredictionContext",
    "get_or_create_context",
    "clear_context",
    "get_active_sessions"
]
