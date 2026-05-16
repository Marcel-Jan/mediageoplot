"""Locate and invoke exiftool for video GPS extraction.

exiftool is bundled next to the app for end-user builds, but during development
we fall back to whatever's on PATH (e.g. `brew install exiftool`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional


def _bundled_candidates() -> list[Path]:
    """Locations to check for a bundled exiftool, in priority order."""
    candidates: list[Path] = []

    # When packaged with flet/PyInstaller, _MEIPASS points at the unpacked
    # resources dir; non-frozen runs use the project root.
    base: Path
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        base = Path(meipass) if meipass else Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent

    # Windows ships exiftool(-k).exe; we rename to exiftool.exe in CI.
    candidates.append(base / "resources" / "exiftool" / "exiftool")
    candidates.append(base / "resources" / "exiftool" / "exiftool.exe")
    # macOS .app bundle layout: resources land inside Contents/Frameworks via flet pack
    candidates.append(base / "exiftool")
    candidates.append(base / "exiftool.exe")

    return candidates


@lru_cache(maxsize=1)
def find_exiftool() -> Optional[str]:
    """Return a path to a usable exiftool, or None if unavailable."""
    for candidate in _bundled_candidates():
        if candidate.is_file():
            return str(candidate)
    return shutil.which("exiftool")


def run_exiftool_json(args: list[str]) -> Optional[list[dict]]:
    """Run exiftool with -j and return the parsed JSON list, or None on failure."""
    exe = find_exiftool()
    if exe is None:
        return None
    try:
        completed = subprocess.run(
            [exe, *args],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if not completed.stdout:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
