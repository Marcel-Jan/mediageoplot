"""Folium-based map rendering. Produces an HTML file with markers."""

from __future__ import annotations

import logging
from typing import Optional

import folium
import pandas as pd


def _marker_style(extension: str) -> tuple[str, str]:
    extension = extension.lower().lstrip(".")
    if extension == "heic":
        return "red", "camera"
    if extension in ("jpg", "jpeg"):
        return "darkred", "camera"
    if extension in ("mp4", "xml"):
        return "blue", "facetime-video"
    if extension == "mts":
        return "darkblue", "facetime-video"
    return "lightgray", "question-sign"


def plot_map(
    media_files_df: pd.DataFrame,
    output_file: str,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Render a folium map of the geocoordinates in `media_files_df` and save to `output_file`.

    Returns the path to the written HTML file.
    """
    if logger is None:
        logger = logging.getLogger("mediageoplot.mapview")
        logger.addHandler(logging.NullHandler())

    if media_files_df.empty:
        logger.warning("Dataframe is empty — producing an empty world map")
        my_map = folium.Map(location=[0, 0], zoom_start=2)
        my_map.save(output_file)
        return output_file

    latitude_mean = media_files_df["latitude"].mean()
    longitude_mean = media_files_df["longitude"].mean()
    my_map = folium.Map(location=[latitude_mean, longitude_mean], zoom_start=12)

    for index, georow in media_files_df.iterrows():
        index_str = str(index)
        # Extract extension from the filename
        if "." in index_str:
            extension = index_str.rsplit(".", 1)[1].rstrip("')]").lower()
        else:
            extension = ""
        marker_colour, marker_icon = _marker_style(extension)

        if pd.isna(georow["latitude"]) or pd.isna(georow["longitude"]):
            logger.debug("Skipping %s (no coords)", index_str)
            continue

        folium.Marker(
            [georow["latitude"], georow["longitude"]],
            popup=f"filename: {index_str}<br>creationdate: {georow['creationdate']}",
            icon=folium.Icon(color=marker_colour, icon_color="white", icon=marker_icon),
        ).add_to(my_map)

    my_map.save(output_file)
    return output_file
