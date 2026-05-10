"""Anthropic-only LLM client. Minimal, no multi-provider."""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM call failed."""


class LLMClient:
    """Anthropic API client with retry on overload."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise LLMError("Missing ANTHROPIC_API_KEY in environment")
            try:
                import anthropic
            except ImportError:
                raise LLMError(
                    "Package 'anthropic' not installed. Run: pip install open-collider[api]"
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def call(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8000,
    ) -> str:
        """Single Anthropic API call with retry on overload.

        - 5 retries on overloaded (3 min backoff each)
        - No retry on rate limit (raises immediately)
        - Streams for opus models (required by API for long requests)
        """
        client = self._get_client()
        import anthropic as anthropic_lib

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        max_retries = 5
        retry_wait = 180

        for attempt in range(1, max_retries + 1):
            try:
                if "opus" in model:
                    collected = []
                    with client.messages.stream(**kwargs) as stream:
                        for text in stream.text_stream:
                            collected.append(text)
                    return "".join(collected)
                response = client.messages.create(**kwargs)
                return response.content[0].text or ""
            except anthropic_lib.RateLimitError as e:
                raise LLMError(f"Rate limit: {e}")
            except anthropic_lib.APIStatusError as e:
                if "overloaded" in str(e).lower() and attempt < max_retries:
                    logger.warning(
                        "Overloaded (attempt %d/%d), retry in %ds",
                        attempt, max_retries, retry_wait,
                    )
                    time.sleep(retry_wait)
                    continue
                raise LLMError(f"API error: {e}")

        raise LLMError(f"Failed after {max_retries} retries")
