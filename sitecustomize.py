"""Ensure the repo root does not shadow Python stdlib modules.

This repository includes bundled .pyd files and DLLs at the project root.
When Python starts from this directory, those entries can shadow stdlib
modules such as socket, causing import errors like
'DLL load failed while importing _socket'.
"""

from __future__ import annotations

import os
import sys


def _remove_project_root_from_sys_path() -> None:
    current_dir = os.path.normcase(os.path.abspath(os.getcwd()))
    filtered = []
    for entry in sys.path:
        if not entry:
            continue
        normalized = os.path.normcase(os.path.abspath(entry))
        if normalized == current_dir:
            continue
        filtered.append(entry)
    sys.path[:] = filtered


_remove_project_root_from_sys_path()
