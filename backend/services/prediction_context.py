"""
Prediction Context Manager - Tracks prediction history for sequential processing.

This module maintains context of all predictions made during questionnaire analysis,
allowing the LLM to consider previous decisions when making new predictions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import OrderedDict

logger = logging.getLogger(__name__)


class PredictionContext:
    """
    Manages prediction context for sequential questionnaire processing.

    Stores each prediction with its reasoning, RAG sources, and metadata
    to provide context for subsequent predictions.
    """

    def __init__(self, session_id: str):
        """
        Initialize prediction context for a session.

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.predictions: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_prediction(
        self,
        question_id: str,
        question_text: str,
        predicted_answer: Any,
        reasoning: str,
        confidence: str = "medium",
        rag_used: bool = False,
        rag_sources: Optional[List[str]] = None,
        rag_chunks: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a new prediction to the context.

        Args:
            question_id: Question identifier
            question_text: The actual question
            predicted_answer: The predicted answer (string or list)
            reasoning: AI's reasoning for this prediction
            confidence: Confidence level (high/medium/low)
            rag_used: Whether RAG was used for this prediction
            rag_sources: List of source document names used
            rag_chunks: Full RAG chunk data (optional)
            metadata: Additional metadata
        """
        self.predictions[question_id] = {
            "question_id": question_id,
            "question_text": question_text,
            "predicted_answer": predicted_answer,
            "reasoning": reasoning,
            "confidence": confidence,
            "rag_used": rag_used,
            "rag_sources": rag_sources or [],
            "rag_chunks": rag_chunks or [],
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        self.updated_at = datetime.now()

        logger.info(
            f"Added prediction for {question_id}: {predicted_answer} "
            f"(RAG: {'Yes' if rag_used else 'No'})"
        )

    def get_prediction(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific prediction by question ID.

        Args:
            question_id: Question identifier

        Returns:
            Prediction dictionary or None if not found
        """
        return self.predictions.get(question_id)

    def has_prediction(self, question_id: str) -> bool:
        """Check if prediction exists for a question."""
        return question_id in self.predictions

    def get_context_summary(
        self,
        include_reasoning: bool = True,
        include_sources: bool = False,
        max_predictions: Optional[int] = None
    ) -> str:
        """
        Generate a formatted context summary for LLM.

        This provides previous predictions as context for analyzing
        the next question.

        Args:
            include_reasoning: Include AI reasoning for each prediction
            include_sources: Include RAG source documents
            max_predictions: Limit to most recent N predictions (None = all)

        Returns:
            Formatted context string
        """
        if not self.predictions:
            return "No previous predictions yet."

        # Get predictions (most recent first if limited)
        predictions_list = list(self.predictions.values())
        if max_predictions:
            predictions_list = predictions_list[-max_predictions:]

        context_parts = []

        for pred in predictions_list:
            qid = pred['question_id']
            question = pred['question_text']
            answer = pred['predicted_answer']
            reasoning = pred['reasoning']
            rag_used = pred['rag_used']
            sources = pred.get('rag_sources', [])

            # Format answer (handle lists)
            if isinstance(answer, list):
                answer_str = ", ".join(answer)
            else:
                answer_str = str(answer)

            # Build context entry
            context = f"Question [{qid}]: {question}\n"
            context += f"Selected Answer: {answer_str}"

            if include_reasoning and reasoning:
                context += f"\nReasoning: {reasoning}"

            if include_sources and rag_used and sources:
                context += f"\nBased on: {', '.join(sources)}"

            context_parts.append(context)

        return "\n\n".join(context_parts)

    def get_narrative_context(self) -> str:
        """
        Generate a narrative-style context summary.

        Converts predictions into a flowing narrative rather than
        structured Q&A format.

        Returns:
            Narrative context string
        """
        if not self.predictions:
            return ""

        narrative_parts = []

        for pred in self.predictions.values():
            question = pred['question_text']
            answer = pred['predicted_answer']

            # Convert to narrative form
            if "how" in question.lower():
                narrative = f"The organization is {answer}"
            elif "does" in question.lower() or "is" in question.lower():
                narrative = f"Regarding '{question}': {answer}"
            else:
                narrative = f"For {question}: {answer}"

            narrative_parts.append(narrative)

        return ". ".join(narrative_parts) + "."

    def get_all_rag_sources(self) -> List[str]:
        """
        Get all unique RAG sources used across all predictions.

        Returns:
            List of unique source document names
        """
        sources = set()
        for pred in self.predictions.values():
            if pred.get('rag_used'):
                sources.update(pred.get('rag_sources', []))
        return sorted(list(sources))

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about predictions made.

        Returns:
            Dictionary with stats:
                - total_predictions: Number of predictions made
                - rag_used_count: How many used RAG
                - unique_rag_sources: Number of unique documents consulted
                - average_confidence: Average confidence level
        """
        if not self.predictions:
            return {
                "total_predictions": 0,
                "rag_used_count": 0,
                "unique_rag_sources": 0,
                "high_confidence_count": 0,
                "medium_confidence_count": 0,
                "low_confidence_count": 0
            }

        rag_count = sum(1 for p in self.predictions.values() if p.get('rag_used'))
        confidence_counts = {"high": 0, "medium": 0, "low": 0}

        for pred in self.predictions.values():
            conf = pred.get('confidence', 'medium')
            if conf in confidence_counts:
                confidence_counts[conf] += 1

        return {
            "total_predictions": len(self.predictions),
            "rag_used_count": rag_count,
            "unique_rag_sources": len(self.get_all_rag_sources()),
            "high_confidence_count": confidence_counts['high'],
            "medium_confidence_count": confidence_counts['medium'],
            "low_confidence_count": confidence_counts['low']
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "session_id": self.session_id,
            "predictions": dict(self.predictions),
            "statistics": self.get_statistics(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load context from dictionary.

        Args:
            data: Dictionary with predictions data
        """
        self.session_id = data.get('session_id', self.session_id)
        self.predictions = OrderedDict(data.get('predictions', {}))

        # Parse timestamps
        try:
            self.created_at = datetime.fromisoformat(data.get('created_at'))
        except (ValueError, TypeError):
            self.created_at = datetime.now()

        try:
            self.updated_at = datetime.fromisoformat(data.get('updated_at'))
        except (ValueError, TypeError):
            self.updated_at = datetime.now()

        logger.info(
            f"Loaded context with {len(self.predictions)} predictions "
            f"for session {self.session_id}"
        )

    def clear(self) -> None:
        """Clear all predictions."""
        self.predictions.clear()
        self.updated_at = datetime.now()
        logger.info(f"Cleared prediction context for session {self.session_id}")


# Context registry for managing multiple sessions
_context_registry: Dict[str, PredictionContext] = {}


def get_or_create_context(session_id: str) -> PredictionContext:
    """
    Get existing context or create new one for session.

    Args:
        session_id: Session identifier

    Returns:
        PredictionContext instance
    """
    if session_id not in _context_registry:
        _context_registry[session_id] = PredictionContext(session_id)
        logger.info(f"Created new prediction context for session {session_id}")
    return _context_registry[session_id]


def clear_context(session_id: str) -> bool:
    """
    Clear context for a session.

    Args:
        session_id: Session identifier

    Returns:
        True if context existed and was cleared, False otherwise
    """
    if session_id in _context_registry:
        del _context_registry[session_id]
        logger.info(f"Cleared context for session {session_id}")
        return True
    return False


def get_active_sessions() -> List[str]:
    """
    Get list of session IDs with active contexts.

    Returns:
        List of session IDs
    """
    return list(_context_registry.keys())
