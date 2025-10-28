"""
RAG Client for retrieving document chunks from RAG API.

This module provides a wrapper around the RAG API running on localhost:5000.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGClient:
    """Client for interacting with the RAG API service."""

    def __init__(self, rag_url: str = "http://localhost:5000"):
        """
        Initialize RAG client.

        Args:
            rag_url: Base URL of the RAG API service
        """
        self.rag_url = rag_url
        self.retrieve_endpoint = f"{rag_url}/api/retrieve"
        self.health_endpoint = f"{rag_url}/api/health"
        self.stats_endpoint = f"{rag_url}/api/stats"

    def check_health(self, timeout: int = 5) -> bool:
        """
        Check if RAG API is running and healthy.

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(self.health_endpoint, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"RAG API health check: {data.get('status')}")
                return data.get('status') == 'healthy'
            return False
        except requests.RequestException as e:
            logger.error(f"RAG API health check failed: {str(e)}")
            return False

    def retrieve_chunks(
        self,
        query: str,
        top_k: int = 5,
        timeout: int = 10,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve relevant document chunks from RAG API.

        Args:
            query: User's question or search query
            top_k: Number of chunks to retrieve (1-20)
            timeout: Request timeout in seconds
            retry: Whether to retry on failure

        Returns:
            Dictionary containing:
                - success: bool
                - chunks: List of chunk dictionaries
                - metadata: Performance and routing info
                - error: Error message if failed

        Raises:
            ConnectionError: If RAG API is not reachable
            TimeoutError: If request times out
        """
        start_time = datetime.now()

        # Check health first
        if not self.check_health(timeout=3):
            error_msg = "RAG API is not running or unhealthy"
            logger.error(error_msg)
            return {
                "success": False,
                "chunks": [],
                "error": error_msg,
                "query": query
            }

        try:
            # Make the request
            response = requests.post(
                self.retrieve_endpoint,
                json={'query': query, 'top_k': top_k},
                headers={'Content-Type': 'application/json'},
                timeout=timeout
            )

            elapsed = (datetime.now() - start_time).total_seconds()

            if response.status_code != 200:
                error_msg = response.json().get('error', 'Unknown error')
                logger.error(f"RAG API returned error: {error_msg}")
                return {
                    "success": False,
                    "chunks": [],
                    "error": error_msg,
                    "query": query
                }

            data = response.json()
            chunks = data.get('chunks', [])

            logger.info(
                f"Retrieved {len(chunks)} chunks for query in {elapsed:.2f}s"
            )

            return {
                "success": True,
                "chunks": chunks,
                "query": query,
                "total_chunks": data.get('total_chunks', len(chunks)),
                "routing_info": data.get('routing_info', {}),
                "performance": data.get('performance', {}),
                "retrieval_time": elapsed
            }

        except requests.Timeout as e:
            error_msg = f"RAG API request timed out after {timeout}s"
            logger.error(error_msg)

            # Retry once if enabled
            if retry:
                logger.info("Retrying RAG API request...")
                return self.retrieve_chunks(
                    query=query,
                    top_k=top_k,
                    timeout=timeout,
                    retry=False  # Don't retry again
                )

            return {
                "success": False,
                "chunks": [],
                "error": error_msg,
                "query": query
            }

        except requests.RequestException as e:
            error_msg = f"RAG API request failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "chunks": [],
                "error": error_msg,
                "query": query
            }

    def format_chunks_as_context(
        self,
        chunks: List[Dict[str, Any]],
        include_sources: bool = True,
        include_similarity: bool = False
    ) -> str:
        """
        Format retrieved chunks into a context string for LLM.

        Args:
            chunks: List of chunk dictionaries from retrieve_chunks()
            include_sources: Whether to include source document names
            include_similarity: Whether to include similarity scores

        Returns:
            Formatted context string
        """
        if not chunks:
            return ""

        formatted_chunks = []

        for i, chunk in enumerate(chunks, 1):
            content = chunk.get('content', '')
            source = chunk.get('source', 'unknown')
            similarity = chunk.get('similarity', 0.0)

            if include_sources and include_similarity:
                header = f"[Document {i}: {source} | Similarity: {similarity:.2f}]"
            elif include_sources:
                header = f"[Document {i}: {source}]"
            else:
                header = f"[Document {i}]"

            formatted_chunks.append(f"{header}\n{content}")

        return "\n\n---\n\n".join(formatted_chunks)

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get RAG system statistics.

        Returns:
            Dictionary with collection counts and statistics, or None if failed
        """
        try:
            response = requests.get(self.stats_endpoint, timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to get RAG stats: {str(e)}")
            return None

    def extract_sources(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract unique source document names from chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            List of unique source document names
        """
        sources = set()
        for chunk in chunks:
            source = chunk.get('source')
            if source:
                sources.add(source)
        return sorted(list(sources))


# Singleton instance
_rag_client_instance: Optional[RAGClient] = None


def get_rag_client() -> RAGClient:
    """
    Get singleton RAG client instance.

    Returns:
        Shared RAGClient instance
    """
    global _rag_client_instance
    if _rag_client_instance is None:
        _rag_client_instance = RAGClient()
    return _rag_client_instance
