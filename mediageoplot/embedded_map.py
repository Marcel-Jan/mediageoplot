"""Builds a Flet-embedded interactive map from a scan dataframe.

Uses OpenStreetMap tiles. Markers are colour-coded by file extension to match
the folium map produced by mapview.plot_map.
"""

from __future__ import annotations

from typing import Iterable

import flet as ft
import flet_map as fm
import pandas as pd


OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def _marker_color(extension: str) -> str:
    extension = extension.lower().lstrip(".")
    if extension == "heic":
        return ft.Colors.RED
    if extension in ("jpg", "jpeg"):
        return ft.Colors.RED_900
    if extension in ("mp4", "xml"):
        return ft.Colors.BLUE
    if extension == "mts":
        return ft.Colors.BLUE_900
    return ft.Colors.GREY


def _marker_icon(extension: str) -> str:
    extension = extension.lower().lstrip(".")
    if extension in ("mp4", "xml", "mts"):
        return ft.Icons.VIDEOCAM
    if extension in ("heic", "jpg", "jpeg"):
        return ft.Icons.PHOTO_CAMERA
    return ft.Icons.HELP_OUTLINE


def _extension_from_index(index_value) -> str:
    s = str(index_value)
    return s.rsplit(".", 1)[1].lower() if "." in s else ""


def _bounds(coords: Iterable[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Return (min_lat, min_lon, max_lat, max_lon) of the given coords."""
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return min(lats), min(lons), max(lats), max(lons)


def build_map_control(df: pd.DataFrame) -> ft.Control:
    """Return a Flet Control that renders an interactive map of `df`'s coordinates.

    `df` must have `latitude`, `longitude`, `creationdate` columns and a filename index.
    If `df` is empty, returns an empty world map.
    """
    valid_rows = []
    if not df.empty:
        valid_rows = [
            (idx, row) for idx, row in df.iterrows()
            if pd.notna(row["latitude"]) and pd.notna(row["longitude"])
        ]

    if not valid_rows:
        return fm.Map(
            initial_center=fm.MapLatitudeLongitude(0, 0),
            initial_zoom=2.0,
            layers=[
                fm.TileLayer(url_template=OSM_TILE_URL, user_agent_package_name="mediageoplot"),
            ],
            expand=True,
        )

    coords = [(float(row["latitude"]), float(row["longitude"])) for _, row in valid_rows]
    min_lat, min_lon, max_lat, max_lon = _bounds(coords)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2

    # Pick a zoom level based on the bounding-box span. Rough heuristic.
    span = max(max_lat - min_lat, max_lon - min_lon)
    if span < 0.01:
        zoom = 14.0
    elif span < 0.1:
        zoom = 11.0
    elif span < 1:
        zoom = 8.0
    elif span < 10:
        zoom = 5.0
    elif span < 50:
        zoom = 3.5
    else:
        zoom = 2.0

    markers = []
    for idx, row in valid_rows:
        ext = _extension_from_index(idx)
        color = _marker_color(ext)
        icon_name = _marker_icon(ext)
        tooltip = f"{idx}\n{row['creationdate']}"
        markers.append(fm.Marker(
            coordinates=fm.MapLatitudeLongitude(
                float(row["latitude"]), float(row["longitude"])),
            content=ft.Container(
                content=ft.Icon(icon_name, color=ft.Colors.WHITE, size=16),
                bgcolor=color,
                width=28,
                height=28,
                border_radius=14,
                alignment=ft.Alignment.CENTER,
                tooltip=tooltip,
            ),
            width=28,
            height=28,
        ))

    return fm.Map(
        initial_center=fm.MapLatitudeLongitude(center_lat, center_lon),
        initial_zoom=zoom,
        layers=[
            fm.TileLayer(url_template=OSM_TILE_URL, user_agent_package_name="mediageoplot"),
            fm.MarkerLayer(markers=markers),
        ],
        expand=True,
    )
