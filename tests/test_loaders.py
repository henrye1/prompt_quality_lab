"""Tests for the file loaders. No Streamlit, no Anthropic API."""
from __future__ import annotations

from prompt_quality_lab.loaders import _coerce_row, load_prompts


class FakeFile:
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, name: str, content: str | bytes):
        self.name = name
        self._content = content.encode("utf-8") if isinstance(content, str) else content

    def read(self) -> bytes:
        return self._content


def test_coerce_row_uses_alternate_keys():
    row = {"prompt_id": "p1", "text": "hello", "expected": "world"}
    assert _coerce_row(row, "fallback", "src.csv") == {
        "id": "p1",
        "prompt": "hello",
        "expected_output": "world",
        "source": "src.csv",
    }


def test_coerce_row_falls_back_when_id_missing():
    row = {"prompt": "x"}
    assert _coerce_row(row, "fallback", "src.csv")["id"] == "fallback"


def test_load_prompts_csv():
    files = [FakeFile("data.csv", "id,prompt,expected_output\np1,hello,world\np2,foo,bar\n")]
    prompts, warnings = load_prompts(files)
    assert warnings == []
    assert prompts == [
        {"id": "p1", "prompt": "hello", "expected_output": "world", "source": "data.csv"},
        {"id": "p2", "prompt": "foo", "expected_output": "bar", "source": "data.csv"},
    ]


def test_load_prompts_json_list():
    content = '[{"id": "p1", "prompt": "hello", "expected_output": "world"}]'
    files = [FakeFile("data.json", content)]
    prompts, warnings = load_prompts(files)
    assert warnings == []
    assert prompts == [
        {"id": "p1", "prompt": "hello", "expected_output": "world", "source": "data.json"}
    ]


def test_load_prompts_txt():
    files = [FakeFile("essay.txt", "  this is a prompt  ")]
    prompts, warnings = load_prompts(files)
    assert warnings == []
    assert prompts == [
        {
            "id": "essay.txt",
            "prompt": "this is a prompt",
            "expected_output": "",
            "source": "essay.txt",
        }
    ]


def test_load_prompts_skips_empty_prompt_rows():
    files = [FakeFile("data.csv", "id,prompt,expected_output\np1,,world\np2,foo,bar\n")]
    prompts, _ = load_prompts(files)
    assert len(prompts) == 1
    assert prompts[0]["id"] == "p2"


def test_load_prompts_warns_on_invalid_json():
    files = [FakeFile("bad.json", "{not valid json")]
    prompts, warnings = load_prompts(files)
    assert prompts == []
    assert len(warnings) == 1
    assert "bad.json" in warnings[0]


def test_load_prompts_warns_on_unknown_extension():
    files = [FakeFile("mystery.xyz", "data")]
    prompts, warnings = load_prompts(files)
    assert prompts == []
    assert len(warnings) == 1
    assert "mystery.xyz" in warnings[0]


def test_load_prompts_handles_latin1_fallback():
    files = [FakeFile("essay.txt", b"caf\xe9")]
    prompts, _ = load_prompts(files)
    assert prompts[0]["prompt"] == "café"
