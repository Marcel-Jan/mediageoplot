"""Scanner: walks directories, extracts GPS data, returns a structured result.

This is the main entry point for both the CLI and the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional
import logging

import pandas as pd

from .media_types import HEICFile, MP4XMLFile, JpegFile, VideoFile


MEDIA_FILE_EXTENSIONS = ["jpg", "jpeg", "heic", "mp4", "xml", "mts"]


@dataclass
class ScanResult:
    """Result of scanning one or more directories for media files with GPS data."""

    files_scanned: int = 0
    files_with_gps: int = 0
    dataframe: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(
        columns=["creationdate", "latitude", "longitude", "altitude"]))
    errors: list[str] = field(default_factory=list)


ProgressCallback = Callable[[int, int, str], None]
"""Signature: (current_index, total_count, current_filename) -> None"""


def _collect_media_files(media_paths: Iterable[Path], recursive: bool = True) -> list[Path]:
    """Find all files matching MEDIA_FILE_EXTENSIONS under the given paths."""
    prefix = "**/" if recursive else ""
    media_files: list[Path] = []
    for media_path in media_paths:
        for ext in MEDIA_FILE_EXTENSIONS:
            media_files.extend(media_path.glob(f"{prefix}*.{ext}"))
            media_files.extend(media_path.glob(f"{prefix}*.{ext.upper()}"))
    return [f for f in media_files if f.is_file()]


def _build_file_object(media_file: Path, logger: logging.Logger):
    """Dispatch to the correct media-type class based on file extension."""
    ext = media_file.suffix.lower().lstrip(".")
    try:
        if ext == "xml":
            return MP4XMLFile(media_file, logger)
        if ext == "heic":
            return HEICFile(media_file, logger)
        if ext in ("jpg", "jpeg"):
            return JpegFile(media_file, logger)
        if ext in ("mp4", "mts"):
            return VideoFile(media_file, logger)
    except Exception as exc:
        logger.warning("Failed to process %s: %s", media_file, exc)
        return None
    return None


def scan_directories(
    media_paths: list[Path],
    logger: Optional[logging.Logger] = None,
    progress_callback: Optional[ProgressCallback] = None,
    recursive: bool = True,
) -> ScanResult:
    """Scan one or more directories for media files with GPS metadata.

    Args:
        media_paths: Directories to scan.
        logger: Optional logger; a no-op logger is used if not provided.
        progress_callback: Optional callable invoked after each file is processed.
        recursive: If True (default), descend into subdirectories; if False,
            only scan files directly in the given directories.

    Returns:
        ScanResult with counts and a dataframe of geolocations.
    """
    if logger is None:
        logger = logging.getLogger("mediageoplot.scanner")
        logger.addHandler(logging.NullHandler())

    result = ScanResult()
    media_files = _collect_media_files(media_paths, recursive=recursive)
    total = len(media_files)
    logger.debug("Found %d candidate media files", total)

    rows: list[dict] = []
    index_labels: list = []

    for i, media_file in enumerate(media_files, start=1):
        result.files_scanned += 1
        file_obj = _build_file_object(media_file, logger)
        if file_obj is not None and getattr(file_obj, "mediafile_geolocation", None) is not None:
            lat, lon, alt = file_obj.mediafile_geolocation
            rows.append({
                "creationdate": getattr(file_obj, "mediafile_creationdate", None),
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
            })
            index_labels.append(str(media_file))
            result.files_with_gps += 1

        if progress_callback is not None:
            try:
                progress_callback(i, total, str(media_file))
            except Exception as exc:
                logger.warning("progress_callback raised: %s", exc)

    if rows:
        result.dataframe = pd.DataFrame(
            rows,
            columns=["creationdate", "latitude", "longitude", "altitude"],
            index=index_labels,
        )

    return result
