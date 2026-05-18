"""Resolve the dataset root directory."""

from __future__ import annotations

import os
from pathlib import Path


def _package_dir() -> Path:
    """Return the directory containing this file. Indirected for test overrides."""
    return Path(__file__).parent


def dataset_root() -> Path:
    """Resolve the dataset root, creating the folder + empty manifest if missing.

    Order of precedence:
    1. $CREDIT_DATASETS_ROOT
    2. <package>/../../data   (when running from a source checkout)
    """
    env = os.environ.get("CREDIT_DATASETS_ROOT")
    root = Path(env).resolve() if env else (_package_dir().parent.parent / "data").resolve()
    root.mkdir(parents=True, exist_ok=True)
    records = root / "records"
    records.mkdir(exist_ok=True)
    manifest = root / "manifest.json"
    if not manifest.exists():
        manifest.write_text('{"version": 1, "records": []}\n', encoding="utf-8")
    return root
