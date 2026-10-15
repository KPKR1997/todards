
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.main_guardrails.article_guard import ArticleSafetyGuard


@pytest.fixture
def guard():
    # Prevent construction of a real Ollama client.
    with patch("backend.main_guardrails.article_guard.OllamaClient"):
        guard = ArticleSafetyGuard(
            client=MagicMock(),
            model="llama-guard3:1b",
        )

    guard.guard_client = MagicMock()
    return guard


def test_safe_article(guard):
    guard.guard_client.generate_raw.return_value = (
        '{"safe": true}'
    )

    result = guard._check_article({
        "title": "Nobel Prize announced",
        "content": "The Nobel Prize was announced today.",
    })

    assert result is True


def test_unsafe_article(guard):
    guard.guard_client.generate_raw.return_value = (
        '{"safe": false}'
    )

    result = guard._check_article({
        "title": "Unsafe article",
        "content": "Test content",
    })

    assert result is False


def test_markdown_json_response(guard):
    guard.guard_client.generate_raw.return_value = (
        '```json\n{"safe": true}\n```'
    )

    assert guard._check_article({
        "title": "Test",
        "content": "Test content",
    }) is True


def test_empty_model_response_returns_error(guard):
    guard.guard_client.generate_raw.return_value = ""

    assert guard._check_article({
        "title": "Test",
        "content": "Test content",
    }) is None


def test_invalid_json_returns_error(guard):
    guard.guard_client.generate_raw.return_value = (
        "This is not valid JSON"
    )

    assert guard._check_article({
        "title": "Test",
        "content": "Test content",
    }) is None


def test_model_exception_returns_error(guard):
    guard.guard_client.generate_raw.side_effect = (
        RuntimeError("Ollama unavailable")
    )

    assert guard._check_article({
        "title": "Test",
        "content": "Test content",
    }) is None


def test_missing_safe_field_returns_error(guard):
    guard.guard_client.generate_raw.return_value = (
        '{"reason": "test"}'
    )

    assert guard._check_article({
        "title": "Test",
        "content": "Test content",
    }) is None


def test_non_boolean_safe_value(guard):
    guard.guard_client.generate_raw.return_value = (
        '{"safe": "unexpected"}'
    )

    # Documents current behavior: unknown strings become False.
    # Consider tightening the parser to return None instead.
    assert guard._check_article({
        "title": "Test",
        "content": "Test content",
    }) is False


def test_generate_raw_receives_prompt(guard):
    guard.guard_client.generate_raw.return_value = (
        '{"safe": true}'
    )

    guard._check_article({
        "title": "Test headline",
        "content": "Test article",
    })

    guard.guard_client.generate_raw.assert_called_once()
    prompt = guard.guard_client.generate_raw.call_args.kwargs[
        "prompt"
    ]

    assert "Test headline" in prompt
    assert "Test article" in prompt
