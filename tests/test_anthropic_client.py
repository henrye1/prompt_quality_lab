"""Tests for the Anthropic client wrapper. Uses a MagicMock client — no real API calls."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from anthropic import RateLimitError

from prompt_quality_lab.anthropic_client import (
    call_claude,
    call_claude_detailed,
    evaluate_against_expected,
)


def _rate_limit_error(retry_after: str | None = None) -> RateLimitError:
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(429, headers=headers, request=request)
    return RateLimitError(message="rate limited", response=response, body=None)


def make_fake_client(text: str, stop_reason: str = "end_turn") -> MagicMock:
    """Return a MagicMock that mimics `Anthropic` and yields `text` from messages.create."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        stop_reason=stop_reason,
    )
    return client


def test_call_claude_passes_model_and_prompt():
    client = make_fake_client("response text")
    out = call_claude(client, "hello", model="claude-sonnet-4-6")
    assert out == "response text"

    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["messages"] == [{"role": "user", "content": "hello"}]
    assert kwargs["system"] == "You are a helpful assistant."
    assert kwargs["max_tokens"] == 8192  # DEFAULT_MAX_TOKENS


def test_call_claude_uses_custom_system():
    client = make_fake_client("ok")
    call_claude(client, "hi", model="m", system="You are a judge.")
    assert client.messages.create.call_args.kwargs["system"] == "You are a judge."


def test_call_claude_defaults_temperature_to_zero_for_reproducibility():
    client = make_fake_client("ok")
    call_claude(client, "hi", model="m")
    assert client.messages.create.call_args.kwargs["temperature"] == 0.0


def test_call_claude_accepts_temperature_override():
    client = make_fake_client("ok")
    call_claude(client, "hi", model="m", temperature=0.7)
    assert client.messages.create.call_args.kwargs["temperature"] == 0.7


def test_call_claude_detailed_returns_stop_reason():
    client = make_fake_client("ok", stop_reason="end_turn")
    text, reason = call_claude_detailed(client, "hi", model="m")
    assert text == "ok"
    assert reason == "end_turn"


def test_call_claude_warns_on_max_tokens_truncation(capsys):
    client = make_fake_client("partial output", stop_reason="max_tokens")
    call_claude(client, "hi", model="m")
    captured = capsys.readouterr()
    assert "truncated" in captured.err
    assert "max_tokens" in captured.err


def test_evaluate_returns_actual_only_when_no_expected():
    client = make_fake_client("actual response")
    actual, score = evaluate_against_expected(client, "prompt", expected="", model="m")
    assert actual == "actual response"
    assert score is None
    assert client.messages.create.call_count == 1


def test_evaluate_parses_integer_score():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="the actual response")]),
        SimpleNamespace(content=[SimpleNamespace(text="8")]),
    ]
    actual, score = evaluate_against_expected(client, "prompt", expected="exp", model="m")
    assert actual == "the actual response"
    assert score == 8.0


def test_evaluate_parses_decimal_with_trailing_punctuation():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="output")]),
        SimpleNamespace(content=[SimpleNamespace(text="7.5.")]),
    ]
    _, score = evaluate_against_expected(client, "p", expected="e", model="m")
    assert score == 7.5


def test_call_claude_retries_on_rate_limit_then_succeeds(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(
        "prompt_quality_lab.anthropic_client.time.sleep", lambda s: sleeps.append(s)
    )
    client = MagicMock()
    client.messages.create.side_effect = [
        _rate_limit_error(retry_after="2"),
        _rate_limit_error(retry_after=None),
        SimpleNamespace(content=[SimpleNamespace(text="success")]),
    ]
    out = call_claude(client, "hi", model="m")
    assert out == "success"
    assert client.messages.create.call_count == 3
    # First sleep honors retry-after header; second falls back to backoff (2 ** 1 = 2).
    assert sleeps == [2.0, 2.0]


def test_call_claude_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr("prompt_quality_lab.anthropic_client.time.sleep", lambda _s: None)
    monkeypatch.setattr("prompt_quality_lab.anthropic_client._MAX_RETRIES", 3)
    client = MagicMock()
    client.messages.create.side_effect = [_rate_limit_error() for _ in range(3)]
    with pytest.raises(RateLimitError):
        call_claude(client, "hi", model="m")
    assert client.messages.create.call_count == 3


def test_evaluate_returns_none_when_score_unparseable():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="output")]),
        SimpleNamespace(content=[SimpleNamespace(text="not a number")]),
    ]
    _, score = evaluate_against_expected(client, "p", expected="e", model="m")
    assert score is None
