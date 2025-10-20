"""
Application settings and configuration.

This module handles environment variables and application settings
following PEP8 standards.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google AI configuration
    google_api_key: str = "AIzaSyCI09gbgsjwnnk67GAu5Ul4CCICU1iB2Js"
    gemini_model: str = "gemini-2.0-flash-exp"

    # Temporal configuration
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "company-search-queue"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


settings = Settings()
