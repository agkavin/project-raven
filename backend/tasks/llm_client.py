from __future__ import annotations

import os
import logging
from typing import Any
import instructor
from google import genai

logger = logging.getLogger(__name__)

_client_cache: dict[str, Any] = {}

DEFAULT_PROVIDER = "google/gemini-2.5-flash"


def resolve_provider(override: str | None, env_var: str, default: str) -> str:
    return override or os.getenv(env_var, default)


def get_instructor_client(provider: str = None):
    provider = resolve_provider(provider, "JD_MATCH_PROVIDER", DEFAULT_PROVIDER)

    client = _client_cache.get(provider)
    if client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if project_id and "vertexai" in provider:
            logger.info(f"Initializing Instructor via from_provider (Vertex AI: {project_id})")
            client = instructor.from_provider(
                provider,
                project=project_id,
                location=location,
                async_client=True
            )
        else:
            logger.info(f"Initializing Instructor via from_provider (Standard/AI Studio: {provider})")
            client = instructor.from_provider(
                provider,
                async_client=True
            )

        _client_cache[provider] = client

    return client
