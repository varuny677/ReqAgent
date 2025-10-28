"""
RAG Filter - Determines which questions should use RAG enhancement.

This module provides smart filtering logic to decide whether a question
needs RAG-based document retrieval or can be answered with company info alone.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RAGFilter:
    """Smart filter for determining RAG usage per question."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize RAG filter with configuration.

        Args:
            config_path: Path to rag_config.json file
        """
        if config_path is None:
            # Default path: qna/rag_config.json
            backend_dir = Path(__file__).parent.parent
            config_path = backend_dir.parent / "qna" / "rag_config.json"

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load RAG configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded RAG config from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"RAG config not found at {self.config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse RAG config: {str(e)}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file not found."""
        return {
            "rag_enabled_sections": ["SEC_CL", "SEC_NW", "SEC_DR", "SEC_LA"],
            "rag_keywords": [
                "compliance", "security", "network", "vpn", "encryption",
                "audit", "logging", "policy", "best practice"
            ],
            "excluded_questions": [],
            "rag_settings": {
                "top_k": 5,
                "timeout_seconds": 10,
                "retry_attempts": 1
            },
            "section_mapping": {
                "BS": "SEC_BS",
                "CL": "SEC_CL",
                "NW": "SEC_NW",
                "DR": "SEC_DR",
                "LA": "SEC_LA"
            }
        }

    def should_use_rag(
        self,
        question_id: str,
        question_text: str,
        question_type: str = "single"
    ) -> Dict[str, Any]:
        """
        Determine if RAG should be used for this question.

        TESTING MODE: Currently forcing RAG for ALL questions to validate retrieval.

        Args:
            question_id: Question identifier (e.g., "CL_Q1", "BS_Q1")
            question_text: The actual question text
            question_type: Question type (single, multi, input, section)

        Returns:
            Dictionary with:
                - use_rag: bool - Whether to use RAG
                - reason: str - Why this decision was made
                - matched_rule: str - Which rule triggered
                - confidence: str - high/medium/low
        """
        # Rule 0: Section questions don't need RAG
        if question_type == "section":
            return {
                "use_rag": False,
                "reason": "Section headers don't require document retrieval",
                "matched_rule": "section_type",
                "confidence": "high"
            }

        # TESTING MODE: Force RAG for ALL non-section questions
        return {
            "use_rag": True,
            "reason": f"Testing mode - using RAG for all questions to validate retrieval and reasoning",
            "matched_rule": "testing_force_all_rag",
            "confidence": "high"
        }

    def _extract_section_id(self, question_id: str) -> str:
        """
        Extract section ID from question ID.

        Examples:
            "CL_Q1" -> "SEC_CL"
            "BS_Q1_ENV" -> "SEC_BS"
            "NW_Q2" -> "SEC_NW"

        Args:
            question_id: Question identifier

        Returns:
            Section ID or empty string if not found
        """
        # Get the prefix (e.g., "CL" from "CL_Q1")
        parts = question_id.split('_')
        if not parts:
            return ""

        prefix = parts[0]
        section_mapping = self.config.get('section_mapping', {})

        return section_mapping.get(prefix, f"SEC_{prefix}")

    def _find_keywords_in_text(
        self,
        text: str,
        keywords: list
    ) -> list:
        """
        Find which keywords are present in the text.

        Args:
            text: Text to search
            keywords: List of keywords to look for

        Returns:
            List of matched keywords
        """
        text_lower = text.lower()
        matched = []

        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)

        return matched

    def get_rag_settings(self) -> Dict[str, Any]:
        """
        Get RAG settings from configuration.

        Returns:
            Dictionary with top_k, timeout, retry settings
        """
        return self.config.get('rag_settings', {
            "top_k": 5,
            "timeout_seconds": 10,
            "retry_attempts": 1
        })

    def reload_config(self) -> bool:
        """
        Reload configuration from file.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config = self._load_config()
            logger.info("RAG config reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload RAG config: {str(e)}")
            return False


# Singleton instance
_rag_filter_instance: Optional[RAGFilter] = None


def get_rag_filter() -> RAGFilter:
    """
    Get singleton RAG filter instance.

    Returns:
        Shared RAGFilter instance
    """
    global _rag_filter_instance
    if _rag_filter_instance is None:
        _rag_filter_instance = RAGFilter()
    return _rag_filter_instance


def should_question_use_rag(
    question_id: str,
    question_text: str,
    question_type: str = "single"
) -> bool:
    """
    Convenience function to check if question should use RAG.

    Args:
        question_id: Question identifier
        question_text: Question text
        question_type: Question type

    Returns:
        True if RAG should be used, False otherwise
    """
    rag_filter = get_rag_filter()
    result = rag_filter.should_use_rag(question_id, question_text, question_type)
    return result.get('use_rag', False)
