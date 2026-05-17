"""Prompt file loaders. Pure: no Streamlit, no Anthropic imports."""
from __future__ import annotations

import csv
import io
import json
import re
from typing import BinaryIO

try:
    import pandas as pd  # optional dependency for Excel
except Exception:
    pd = None

try:
    import docx  # python-docx for .docx
except Exception:
    docx = None

try:
    import PyPDF2  # for PDF text extraction
except Exception:
    PyPDF2 = None


def _make_record(prompt_id: str, prompt: str, expected_output: str, source: str) -> dict:
    return {
        "id": str(prompt_id),
        "prompt": str(prompt),
        "expected_output": str(expected_output),
        "source": source,
    }


def _coerce_row(row: dict, fallback_id: str, source: str) -> dict:
    """Normalise a record to {id, prompt, expected_output, source}."""
    pid = row.get("id") or row.get("prompt_id") or fallback_id
    text = (
        row.get("prompt")
        or row.get("prompt_text")
        or row.get("text")
        or row.get("input")
        or ""
    )
    expected = (
        row.get("expected_output")
        or row.get("expected")
        or row.get("output")
        or ""
    )
    return _make_record(pid, text, expected, source)


def _split_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n+", text.strip()) if block.strip()]


def _parse_block(block: str, fallback_id: str, source: str) -> dict | None:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None

    pid = fallback_id
    expected_lines: list[str] = []
    prompt_lines: list[str] = []
    found_expected = False

    for line in lines:
        if re.match(r"^(?:id|prompt_id|prompt\s*id)\s*[:\-]", line, re.I):
            pid = re.sub(r"^(?:id|prompt_id|prompt\s*id)\s*[:\-]\s*", "", line, flags=re.I).strip() or pid
            continue
        if re.match(r"^(?:expected_output|expected|output)\s*[:\-]", line, re.I):
            found_expected = True
            expected_lines.append(
                re.sub(r"^(?:expected_output|expected|output)\s*[:\-]\s*", "", line, flags=re.I).strip()
            )
            continue
        if found_expected:
            expected_lines.append(line)
        else:
            prompt_lines.append(line)

    prompt_text = "\n".join(prompt_lines).strip()
    expected_text = "\n".join(expected_lines).strip()
    if not prompt_text:
        return None
    return _make_record(pid, prompt_text, expected_text, source)


def load_prompts(uploaded_files) -> tuple[list[dict], list[str]]:
    """Auto-detect file type and return (prompts, warnings).

    Each prompt is {id, prompt, expected_output}. Warnings are human-readable
    strings that the UI layer can surface to the user.
    """
    prompts: list[dict] = []
    warnings: list[str] = []

    for f in uploaded_files:
        name = f.name.lower()
        raw = f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")

        if name.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(content))
            for i, row in enumerate(reader):
                rec = _coerce_row(row, f"{f.name}#{i}", f.name)
                if rec["prompt"]:
                    prompts.append(rec)

        elif name.endswith(".json"):
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                warnings.append(f"Skipping {f.name}: invalid JSON ({e})")
                continue
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        rec = _coerce_row(item, f"{f.name}#{i}", f.name)
                    else:
                        rec = _make_record(f"{f.name}#{i}", str(item), "", f.name)
                    if rec["prompt"]:
                        prompts.append(rec)
            elif isinstance(data, dict):
                rec = _coerce_row(data, f.name, f.name)
                if rec["prompt"]:
                    prompts.append(rec)

        elif name.endswith((".txt", ".md")):
            prompts.append(
                _make_record(f.name, content.strip(), "", f.name)
            )

        elif name.endswith((".xls", ".xlsx", ".xlsm")):
            if pd is None:
                warnings.append(
                    f"Skipping {f.name}: pandas not installed (required for Excel files)"
                )
                continue
            try:
                # read into DataFrame; try first sheet
                df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
            except Exception:
                try:
                    df = pd.read_excel(io.BytesIO(raw))
                except Exception as e:
                    warnings.append(f"Skipping {f.name}: could not read Excel ({e})")
                    continue
            if df.empty:
                warnings.append(f"Skipping {f.name}: empty Excel file")
                continue
            records = df.to_dict(orient="records")
            for i, row in enumerate(records):
                rec = _coerce_row(row, f"{f.name}#{i}", f.name)
                if rec["prompt"]:
                    prompts.append(rec)

        elif name.endswith(".docx"):
            if docx is None:
                warnings.append(
                    f"Skipping {f.name}: python-docx not installed (required for .docx)"
                )
                continue
            try:
                doc = docx.Document(io.BytesIO(raw))
                text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
                blocks = _split_blocks(text)
                if len(blocks) > 1:
                    for i, block in enumerate(blocks):
                        rec = _parse_block(block, f"{f.name}#{i}", f.name)
                        if rec:
                            prompts.append(rec)
                elif text.strip():
                    prompts.append(_make_record(f.name, text.strip(), "", f.name))
            except Exception as e:
                warnings.append(f"Skipping {f.name}: could not read docx ({e})")
                continue

        elif name.endswith(".pdf"):
            if PyPDF2 is None:
                warnings.append(f"Skipping {f.name}: PyPDF2 not installed (required for PDF)")
                continue
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(raw))
                texts = []
                for page in reader.pages:
                    try:
                        texts.append(page.extract_text() or "")
                    except Exception:
                        texts.append("")
                full = "\n\n".join(t for t in texts if t.strip())
                blocks = _split_blocks(full)
                if len(blocks) > 1:
                    for i, block in enumerate(blocks):
                        rec = _parse_block(block, f"{f.name}#{i}", f.name)
                        if rec:
                            prompts.append(rec)
                elif full.strip():
                    prompts.append(_make_record(f.name, full.strip(), "", f.name))
            except Exception as e:
                warnings.append(f"Skipping {f.name}: could not read PDF ({e})")
                continue

        else:
            warnings.append(f"Skipping unsupported file type: {f.name}")

    return prompts, warnings
