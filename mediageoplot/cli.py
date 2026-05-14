"""Command-line entry point. Preserves the original `media_gpsplot.py` interface."""

from __future__ import annotations

import argparse
import datetime
import logging
import os
from pathlib import Path

from .scanner import scan_directories
from .mapview import plot_map


def _setup_logger(basedir: str) -> logging.Logger:
    log_dir = os.path.join(basedir, "log")
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_handler = logging.FileHandler(os.path.join(log_dir, f"media_gpsplot3_{stamp}.log"))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def main() -> None:
    basedir = os.path.abspath(os.getcwd())
    logger = _setup_logger(basedir)
    logger.debug("Start of mediageoplot CLI")
    logger.debug("===============================")

    parser = argparse.ArgumentParser(
        description="Get geolocations from media files and plot them on a map (HTML).")
    parser.add_argument("--media_path", "-m", type=str, default=".",
                        help="Path(s) of media files, comma-separated. Default: current dir.")
    parser.add_argument("--output", "-o", type=str, default="media_gpsplot.html",
                        help="HTML output file. Default: media_gpsplot.html")
    args = parser.parse_args()

    media_paths = [Path(p).resolve() for p in args.media_path.split(",")]
    media_paths = [p for p in media_paths if p.is_dir()]
    if not media_paths:
        print("No valid media paths given. Exiting.")
        logger.debug("No valid media paths given. Exiting.")
        return

    print(f"Media paths: {media_paths}")
    logger.debug("Media paths: %s", media_paths)

    result = scan_directories(media_paths, logger=logger)
    print(f"Scanned {result.files_scanned} files — {result.files_with_gps} had GPS data.")
    logger.info("Scanned %d files — %d had GPS data.",
                result.files_scanned, result.files_with_gps)

    plot_map(result.dataframe, args.output, logger=logger)
    print(f"Map written to {args.output}")


if __name__ == "__main__":
    main()
