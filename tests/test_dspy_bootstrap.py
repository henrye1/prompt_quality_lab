"""Tests for DSPy-style few-shot bootstrap. Pure function — no API needed."""
from __future__ import annotations

from prompt_quality_lab.optimisers.dspy_bootstrap import dspy_style_bootstrap


def test_returns_original_when_no_examples():
    assert dspy_style_bootstrap("write a haiku", []) == "write a haiku"


def test_returns_original_when_examples_lack_expected_output():
    examples = [{"id": "a", "prompt": "x", "expected_output": ""}]
    assert dspy_style_bootstrap("target", examples) == "target"


def test_builds_few_shot_block_from_labelled_examples():
    examples = [
        {"id": "a", "prompt": "input A", "expected_output": "output A"},
        {"id": "b", "prompt": "input B", "expected_output": "output B"},
    ]
    result = dspy_style_bootstrap("new target", examples)
    assert "Input:\ninput A\n\nOutput:\noutput A" in result
    assert "Input:\ninput B\n\nOutput:\noutput B" in result
    assert "new target" in result


def test_filters_out_examples_with_empty_expected():
    examples = [
        {"id": "a", "prompt": "labelled", "expected_output": "yes"},
        {"id": "b", "prompt": "unlabelled", "expected_output": ""},
    ]
    result = dspy_style_bootstrap("target", examples)
    assert "labelled" in result
    assert "unlabelled" not in result
