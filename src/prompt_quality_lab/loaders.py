"""Prompt file loaders. Pure: no Streamlit, no Anthropic imports."""
from __future__ import annotations

import csv
import io
import json
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


def _coerce_row(row: dict, fallback_id: str) -> dict:
    """Normalise a record to {id, prompt, expected_output}."""
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
    return {"id": str(pid), "prompt": str(text), "expected_output": str(expected)}


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
                rec = _coerce_row(row, f"{f.name}#{i}")
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
                        rec = _coerce_row(item, f"{f.name}#{i}")
                    else:
                        rec = {
                            "id": f"{f.name}#{i}",
                            "prompt": str(item),
                            "expected_output": "",
                        }
                    if rec["prompt"]:
                        prompts.append(rec)
            elif isinstance(data, dict):
                rec = _coerce_row(data, f.name)
                if rec["prompt"]:
                    prompts.append(rec)

        elif name.endswith((".txt", ".md")):
            prompts.append(
                {"id": f.name, "prompt": content.strip(), "expected_output": ""}
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
                rec = _coerce_row(row, f"{f.name}#{i}")
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
                if text.strip():
                    prompts.append({"id": f.name, "prompt": text.strip(), "expected_output": ""})
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
                if full.strip():
                    prompts.append({"id": f.name, "prompt": full.strip(), "expected_output": ""})
            except Exception as e:
                warnings.append(f"Skipping {f.name}: could not read PDF ({e})")
                continue

        else:
            warnings.append(f"Skipping unsupported file type: {f.name}")

    return prompts, warnings
