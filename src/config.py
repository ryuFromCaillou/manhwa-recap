from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gpt-4.1"
DEFAULT_BATCH_SIZE = 4
DEFAULT_MAX_HEIGHT = 4000
DEFAULT_OUTPUT_FORMAT = "text"  # text|json|both


@dataclass(frozen=True)
class AppConfig:
    """Application configuration loaded from environment variables."""

    openai_api_key: str

    def __init__(self, openai_api_key: str) -> None:
        """
        Create an AppConfig.

        Args:
            openai_api_key: OpenAI API key used by the OpenAI Python client.
        """
        object.__setattr__(self, "openai_api_key", openai_api_key)

    @staticmethod
    def load() -> "AppConfig":
        """
        Load configuration from `.env` and environment variables.

        Returns:
            AppConfig with required values populated.

        Raises:
            RuntimeError: If `OPENAI_API_KEY` is missing or empty.
        """
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            pass
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "Missing OPENAI_API_KEY. Set it in your environment or in a .env file."
            )
        return AppConfig(openai_api_key=api_key)
