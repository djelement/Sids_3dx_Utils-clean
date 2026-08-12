"""Common utility functions used across the project."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_name(value: str) -> str:
    """Normalize human-readable names by trimming extra whitespace."""
    if value is None:
        raise ValueError("Name cannot be None.")

    normalized = " ".join(str(value).strip().split())
    if not normalized:
        raise ValueError("Name cannot be empty.")

    return normalized


def coerce_path(path_value: str | Path) -> str:
    """Convert a path-like value into a normalized absolute-ish string."""
    return str(Path(path_value).expanduser())


def ensure_list(value: Any) -> list[Any]:
    """Return a list for scalar and collection inputs while preserving list content."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [value]
    return [value]
