"""
Todards Pipeline — Centralized Ollama Client

Single wrapper for all Ollama interactions.
- Automatically generates JSON schema from Pydantic models
- Passes schema to Ollama via the `format` parameter
- Validates responses via Pydantic
- Retries on parse failure
- Logs all LLM calls for evaluation metrics
"""

import json
import time
import logging
from typing import Type, TypeVar, Optional

import requests
from pydantic import BaseModel

from config.settings import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_MAX_RETRIES,
    OLLAMA_RETRY_DELAY,
)


logger = logging.getLogger("todards.ollama")

T = TypeVar("T", bound=BaseModel)


class OllamaClient:
    """
    Centralized Ollama interaction client.

    Usage:
        client = OllamaClient()
        result = client.generate(
            prompt="Summarize this article: ...",
            response_model=SummaryResponse,
        )
        print(result.summary)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = OLLAMA_TIMEOUT,
        max_retries: int = OLLAMA_MAX_RETRIES,
        retry_delay: int = OLLAMA_RETRY_DELAY,
        metrics_collector=None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.metrics = metrics_collector

        # Track LLM call statistics
        self.total_calls = 0
        self.total_retries = 0
        self.total_failures = 0
        self.total_time = 0.0

    @staticmethod
    def _pydantic_to_json_schema(model_class: Type[BaseModel]) -> dict:
        """
        Convert a Pydantic model class to a JSON schema dict
        suitable for Ollama's `format` parameter.
        """
        schema = model_class.model_json_schema()

        # Ollama expects a clean JSON schema without Pydantic internals
        # Remove $defs if present and inline them
        defs = schema.pop("$defs", {})

        def resolve_refs(obj):
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref_name = obj["$ref"].split("/")[-1]
                    if ref_name in defs:
                        return resolve_refs(defs[ref_name])
                    return obj
                return {
                    key: resolve_refs(value)
                    for key, value in obj.items()
                }
            elif isinstance(obj, list):
                return [resolve_refs(item) for item in obj]
            return obj

        resolved = resolve_refs(schema)
        return resolved

    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize user-provided content to prevent prompt injection.
        Wraps content in delimiters and strips control characters.
        """
        if not text:
            return ""

        # Strip null bytes and other control chars (keep newlines/tabs)
        cleaned = "".join(
            char for char in text
            if char == "\n" or char == "\t" or (ord(char) >= 32)
        )

        return cleaned

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        role: str = "system",
    ) -> T:
        """
        Send a prompt to Ollama and return a validated Pydantic model.

        Args:
            prompt: The system/user prompt to send.
            response_model: Pydantic model class for structured output.
            role: Message role ("system" or "user").

        Returns:
            Validated instance of response_model.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        json_schema = self._pydantic_to_json_schema(response_model)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": role,
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": json_schema,
        }

        last_error = None

        for attempt in range(1, self.max_retries + 2):

            self.total_calls += 1
            start_time = time.time()

            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                elapsed = time.time() - start_time
                self.total_time += elapsed

                data = response.json()
                content = data.get("message", {}).get("content", "")

                if not content:
                    raise ValueError(
                        "Empty response from Ollama."
                    )

                # Parse JSON from the response
                parsed = self._extract_json(content)

                # Validate through Pydantic
                result = response_model.model_validate(parsed)

                if self.metrics:
                    self.metrics.log_llm_call(
                        model=self.model,
                        prompt_length=len(prompt),
                        response_length=len(content),
                        elapsed=elapsed,
                        success=True,
                    )

                logger.debug(
                    f"Ollama call succeeded: "
                    f"{response_model.__name__} "
                    f"({elapsed:.1f}s)"
                )

                return result

            except Exception as e:

                elapsed = time.time() - start_time
                self.total_time += elapsed
                last_error = e

                if attempt <= self.max_retries:
                    self.total_retries += 1
                    logger.warning(
                        f"Ollama attempt {attempt} failed "
                        f"({response_model.__name__}): {e}. "
                        f"Retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    self.total_failures += 1

                    if self.metrics:
                        self.metrics.log_llm_call(
                            model=self.model,
                            prompt_length=len(prompt),
                            response_length=0,
                            elapsed=elapsed,
                            success=False,
                        )

        raise RuntimeError(
            f"Ollama failed after {self.max_retries + 1} attempts "
            f"for {response_model.__name__}: {last_error}"
        )

    def generate_raw(
        self,
        prompt: str,
        role: str = "system",
    ) -> str:
        """
        Send a prompt to Ollama and return raw text response.
        Used only as fallback when structured output is not needed.
        """
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": role,
                    "content": prompt,
                }
            ],
            "stream": False,
        }

        self.total_calls += 1
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            elapsed = time.time() - start_time
            self.total_time += elapsed

            data = response.json()
            content = data.get("message", {}).get("content", "")

            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.total_failures += 1
            raise

    @staticmethod
    def _extract_json(text: str) -> dict:
        """
        Extract a JSON object from LLM response text.
        Handles markdown code fences and extra text.
        """
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            json_text = text[start:end + 1]
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        # Find JSON array boundaries
        start = text.find("[")
        end = text.rfind("]")

        if start != -1 and end != -1 and end > start:
            json_text = text[start:end + 1]
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Could not extract valid JSON from response: "
            f"{text[:200]}..."
        )

    def get_stats(self) -> dict:
        """Return LLM call statistics."""
        return {
            "total_calls": self.total_calls,
            "total_retries": self.total_retries,
            "total_failures": self.total_failures,
            "total_time_seconds": round(self.total_time, 2),
            "avg_time_seconds": (
                round(self.total_time / self.total_calls, 2)
                if self.total_calls > 0
                else 0
            ),
        }
