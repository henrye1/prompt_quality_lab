"""Tests for the Anthropic client wrapper. Uses a MagicMock client — no real API calls."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from prompt_quality_lab.anthropic_client import call_claude, evaluate_against_expected


def make_fake_client(text: str) -> MagicMock:
    """Return a MagicMock that mimics `Anthropic` and yields `text` from messages.create."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=text)]
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
    assert kwargs["max_tokens"] == 2048


def test_call_claude_uses_custom_system():
    client = make_fake_client("ok")
    call_claude(client, "hi", model="m", system="You are a judge.")
    assert client.messages.create.call_args.kwargs["system"] == "You are a judge."


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


def test_evaluate_returns_none_when_score_unparseable():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="output")]),
        SimpleNamespace(content=[SimpleNamespace(text="not a number")]),
    ]
    _, score = evaluate_against_expected(client, "p", expected="e", model="m")
    assert score is None
