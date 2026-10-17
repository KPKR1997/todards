"""Todards Pipeline — centralized Ollama client.

Preserves the public OllamaClient constructor, generate(), generate_raw(),
and get_stats() interfaces while making structured-output parsing strict.
"""

import json
import logging
import time
from typing import Optional, Type, TypeVar

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
    """Centralized wrapper for Ollama chat API calls."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = OLLAMA_TIMEOUT,
        max_retries: int = OLLAMA_MAX_RETRIES,
        retry_delay: int = OLLAMA_RETRY_DELAY,
        metrics_collector=None,
        options: Optional[dict] = None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.retry_delay = max(0, float(retry_delay))
        self.metrics = metrics_collector
        self.options = options or {}

        self.total_calls = 0
        self.total_retries = 0
        self.total_failures = 0
        self.total_time = 0.0

    @staticmethod
    def _pydantic_to_json_schema(model_class: Type[BaseModel]) -> dict:
        """Return a JSON schema suitable for Ollama's ``format`` field."""
        schema = model_class.model_json_schema()
        defs = schema.pop("$defs", {})

        def resolve_refs(obj, depth=0):
            # Guard against unexpectedly recursive model schemas.
            if depth > 30:
                raise ValueError("JSON schema reference nesting is too deep.")
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref_name = obj["$ref"].split("/")[-1]
                    if ref_name not in defs:
                        raise ValueError(f"Unresolved JSON schema reference: {ref_name}")
                    return resolve_refs(defs[ref_name], depth + 1)
                return {key: resolve_refs(value, depth + 1) for key, value in obj.items()}
            if isinstance(obj, list):
                return [resolve_refs(value, depth + 1) for value in obj]
            return obj

        return resolve_refs(schema)

    @staticmethod
    def _extract_content(data) -> str:
        """Safely extract message content from an Ollama /api/chat response."""
        if not isinstance(data, dict):
            raise ValueError("Ollama returned a response that was not a JSON object.")
        message = data.get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama response did not contain a valid 'message' object.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama returned empty or non-text message content.")
        return content.strip()
    
    @staticmethod
    def _response_usage(data) -> dict:
        """Extract token counts and server timings from an Ollama response."""
        if not isinstance(data, dict):
            data = {}

        def token_count(key):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                return value
            return None

        def duration_seconds(key):
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if value >= 0:
                    return value / 1_000_000_000
            return None

        return {
            "prompt_tokens": token_count("prompt_eval_count"),
            "response_tokens": token_count("eval_count"),
            "prompt_eval_seconds": duration_seconds("prompt_eval_duration"),
            "generation_seconds": duration_seconds("eval_duration"),
            "load_seconds": duration_seconds("load_duration"),
            "server_total_seconds": duration_seconds("total_duration"),
        }

    @staticmethod
    def _safe_log_metric(metrics, **kwargs) -> None:
        """Metrics must never turn a successful model response into a failed call."""
        if metrics is None:
            return
        try:
            metrics.log_llm_call(**kwargs)
        except Exception as exc:
            logger.warning("Could not record Ollama metrics: %s", exc)

    def _post_chat(self, payload: dict):
        payload.setdefault("keep_alive", "30m")
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError("Ollama returned invalid JSON in its HTTP response.") from exc

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        role: str = "system",
    ) -> T:
        """Generate structured output and return a validated Pydantic instance."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(response_model, type) or not issubclass(response_model, BaseModel):
            raise TypeError("response_model must be a Pydantic BaseModel class")

        json_schema = self._pydantic_to_json_schema(response_model)
        payload = {
            "model": self.model,
            "messages": [{"role": role, "content": prompt}],
            "stream": False,
            # The original client generated this schema but did not send it.
            "format": json_schema,
            "options": self.options,
        }

        last_error = None
        attempts = self.max_retries + 1

        for attempt in range(1, attempts + 1):
            self.total_calls += 1
            start_time = time.monotonic()
            content = ""
            elapsed = 0.0
            data = None

            try:
                data = self._post_chat(payload)
                content = self._extract_content(data)
                parsed = self._extract_json(content)
                # _extract_json guarantees a dict; this validates required fields/types.
                result = response_model.model_validate(parsed)
                elapsed = time.monotonic() - start_time
                self.total_time += elapsed
                self._safe_log_metric(
                    self.metrics,
                    model=self.model,
                    prompt_length=len(prompt),
                    response_length=len(content),
                    elapsed=elapsed,
                    success=True,
                    **self._response_usage(data),
                )
                logger.debug(
                    "Ollama call succeeded: %s (%.1fs)",
                    response_model.__name__,
                    elapsed,
                )
                return result
            except Exception as exc:
                elapsed = time.monotonic() - start_time
                self.total_time += elapsed
                last_error = exc
                if attempt < attempts:
                    self.total_retries += 1
                    logger.warning(
                        "Ollama attempt %d failed (%s): %s. Retrying in %ss...",
                        attempt,
                        response_model.__name__,
                        exc,
                        self.retry_delay,
                    )
                    if self.retry_delay:
                        time.sleep(self.retry_delay)
                else:
                    self.total_failures += 1
                    # Preserve the original metrics behavior: log one failed
                    # structured call after all retries have been exhausted.
                    self._safe_log_metric(
                        self.metrics,
                        model=self.model,
                        prompt_length=len(prompt),
                        response_length=0,
                        elapsed=elapsed,
                        success=False,
                        **self._response_usage(data),
                    )

        raise RuntimeError(
            f"Ollama failed after {attempts} attempt(s) for "
            f"{response_model.__name__}: {last_error}"
        ) from last_error

    def generate_raw(self, prompt: str, role: str = "system") -> str:
        """Generate raw text and record call duration and Ollama usage."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        payload = {
            "model": self.model,
            "messages": [{"role": role, "content": prompt}],
            "stream": False,
            "options": self.options,
        }

        self.total_calls += 1
        start_time = time.monotonic()
        data = None
        content = ""
        success = False

        try:
            data = self._post_chat(payload)
            content = self._extract_content(data)
            success = True
            return content

        except Exception:
            self.total_failures += 1
            raise

        finally:
            elapsed = time.monotonic() - start_time
            self.total_time += elapsed

            self._safe_log_metric(
                self.metrics,
                model=self.model,
                prompt_length=len(prompt),
                response_length=len(content),
                elapsed=elapsed,
                success=success,
                **self._response_usage(data),
            )

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract a JSON object, raising a useful error on every invalid case."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ollama returned an empty response; expected a JSON object.")

        text = text.strip()

        def parse_candidate(candidate: str):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                return None, False
            if not isinstance(parsed, dict):
                raise ValueError(
                    "Expected a JSON object for structured output, but Ollama returned "
                    f"{type(parsed).__name__}."
                )
            return parsed, True

        # Full response first.
        parsed, valid_json = parse_candidate(text)
        if valid_json:
            return parsed

        # Remove optional Markdown fences.
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            unfenced = "\n".join(lines).strip()
            parsed, valid_json = parse_candidate(unfenced)
            if valid_json:
                return parsed
            text = unfenced

        # Try each plausible object start, rather than returning None when
        # the response contains prose or multiple brace characters.
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                parsed, end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
            # A valid JSON value that is not an object is not acceptable here.
            raise ValueError(
                "Expected a JSON object for structured output, but Ollama returned "
                f"{type(parsed).__name__}."
            )

        preview = text[:180].replace("\n", " ")
        raise ValueError(
            "Could not extract a valid JSON object from Ollama response. "
            f"Response preview: {preview!r}"
        )

    def get_stats(self) -> dict:
        """Return LLM call statistics (same keys as the original client)."""
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
