"""
Firestore service for managing sessions and messages.

This module provides CRUD operations for sessions and messages
using Google Cloud Firestore.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore


logger = logging.getLogger(__name__)


class FirestoreService:
    """Service class for Firestore operations."""

    def __init__(self, credentials_path: str, database_name: str = "reqdb"):
        """
        Initialize Firestore service.

        Args:
            credentials_path: Path to the Firebase credentials JSON file
            database_name: Name of the Firestore database (default: reqdb)
        """
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Firebase Admin SDK already initialized")

            # Get Firestore client with database_id
            # firebase_admin.firestore uses database_id parameter (not database)
            self.db = firestore.client(database_id=database_name)
            logger.info(f"Connected to Firestore database: {database_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {str(e)}")
            raise

    # ==================== SESSION OPERATIONS ====================

    def create_session(
        self, session_id: str, title: str = "New Chat", preview: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier
            title: Session title (default: "New Chat")
            preview: Preview text of the conversation

        Returns:
            Dictionary containing session data
        """
        try:
            session_data = {
                "id": session_id,
                "title": title,
                "preview": preview,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "company_list": [],
            }

            self.db.collection("sessions").document(session_id).set(session_data)
            logger.info(f"Created session: {session_id}")

            # Return with actual timestamp
            session_data["created_at"] = datetime.now()
            session_data["updated_at"] = datetime.now()
            return session_data

        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary or None if not found
        """
        try:
            doc = self.db.collection("sessions").document(session_id).get()

            if doc.exists:
                data = doc.to_dict()
                logger.info(f"Retrieved session: {session_id}")
                return data
            else:
                logger.warning(f"Session not found: {session_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            raise

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List all sessions ordered by updated_at (most recent first).

        Args:
            limit: Maximum number of sessions to return (default: 20)

        Returns:
            List of session dictionaries
        """
        try:
            sessions_ref = self.db.collection("sessions")
            query = sessions_ref.order_by(
                "updated_at", direction=firestore.Query.DESCENDING
            ).limit(limit)

            sessions = []
            for doc in query.stream():
                session_data = doc.to_dict()
                sessions.append(session_data)

            logger.info(f"Retrieved {len(sessions)} sessions")
            return sessions

        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            raise

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        preview: Optional[str] = None,
        company_list: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Update session fields.

        Args:
            session_id: Session identifier
            title: New title (optional)
            preview: New preview (optional)
            company_list: New company list (optional)
        """
        try:
            update_data = {"updated_at": firestore.SERVER_TIMESTAMP}

            if title is not None:
                update_data["title"] = title
            if preview is not None:
                update_data["preview"] = preview
            if company_list is not None:
                update_data["company_list"] = company_list

            self.db.collection("sessions").document(session_id).update(update_data)
            logger.info(f"Updated session: {session_id}")

        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise

    def delete_session(self, session_id: str) -> None:
        """
        Delete a session and all its messages.

        Args:
            session_id: Session identifier
        """
        try:
            # Delete all messages in the session
            messages_ref = (
                self.db.collection("sessions")
                .document(session_id)
                .collection("messages")
            )

            # Delete messages in batches
            batch = self.db.batch()
            deleted_count = 0

            for doc in messages_ref.stream():
                batch.delete(doc.reference)
                deleted_count += 1

                # Commit batch every 500 operations (Firestore limit)
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()

            # Commit remaining deletions
            if deleted_count % 500 != 0:
                batch.commit()

            # Delete the session document
            self.db.collection("sessions").document(session_id).delete()

            logger.info(f"Deleted session {session_id} with {deleted_count} messages")

        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            raise

    # ==================== MESSAGE OPERATIONS ====================

    def add_message(
        self,
        session_id: str,
        message_id: str,
        role: str,
        content: Any,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Add a message to a session.

        Args:
            session_id: Session identifier
            message_id: Unique message identifier
            role: Message role ("user" or "assistant")
            content: Message content (can be string or dict)
            timestamp: Message timestamp (default: now)

        Returns:
            Message data dictionary
        """
        try:
            message_data = {
                "id": message_id,
                "role": role,
                "content": content,
                "timestamp": timestamp or datetime.now(),
            }

            # Add message to subcollection
            self.db.collection("sessions").document(session_id).collection(
                "messages"
            ).document(message_id).set(message_data)

            # Update session's updated_at timestamp
            self.db.collection("sessions").document(session_id).update(
                {"updated_at": firestore.SERVER_TIMESTAMP}
            )

            logger.info(f"Added message {message_id} to session {session_id}")
            return message_data

        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            raise

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a session, ordered by timestamp.

        Args:
            session_id: Session identifier

        Returns:
            List of message dictionaries
        """
        try:
            messages_ref = (
                self.db.collection("sessions")
                .document(session_id)
                .collection("messages")
                .order_by("timestamp")
            )

            messages = []
            for doc in messages_ref.stream():
                message_data = doc.to_dict()
                messages.append(message_data)

            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages

        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            raise

    def get_session_with_messages(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data along with all its messages.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary containing session data and messages, or None if not found
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return None

            messages = self.get_messages(session_id)

            return {"session": session, "messages": messages}

        except Exception as e:
            logger.error(f"Error getting session with messages: {str(e)}")
            raise

    # ==================== COMPANY LIST OPERATIONS ====================

    def get_company_list(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the company list for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of company dictionaries
        """
        try:
            session = self.get_session(session_id)
            if session:
                return session.get("company_list", [])
            return []

        except Exception as e:
            logger.error(f"Error getting company list: {str(e)}")
            raise

    def set_company_list(
        self, session_id: str, company_list: List[Dict[str, Any]]
    ) -> None:
        """
        Set the company list for a session.

        Args:
            session_id: Session identifier
            company_list: List of company dictionaries
        """
        try:
            self.update_session(session_id, company_list=company_list)
            logger.info(
                f"Set company list for session {session_id} ({len(company_list)} companies)"
            )

        except Exception as e:
            logger.error(f"Error setting company list: {str(e)}")
            raise
