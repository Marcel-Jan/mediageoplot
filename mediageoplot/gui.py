"""Flet desktop GUI for mediageoplot.

Folder picker, scanner with live progress, counts, embedded interactive map,
and an "Open in browser" button for the full folium HTML map. UI text is
language-switchable (English / Dutch) via a dropdown in the top-right.
"""

from __future__ import annotations

import logging
import os
import tempfile
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import flet as ft

from .scanner import scan_directories, ScanResult
from .mapview import plot_map
from .embedded_map import build_map_control
from .i18n import Translator, SUPPORTED_LANGUAGES


DEFAULT_OUTPUT_NAME = "media_gpsplot.html"


@dataclass
class _PostScanState:
    """The last scan's outcome, so we can re-render its UI text on language change."""
    scanned: int
    with_gps: int
    map_path: Optional[str]  # None when no GPS found
    error_message: Optional[str] = None


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("mediageoplot.gui")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    return logger


async def main(page: ft.Page) -> None:
    t = Translator("en")
    page.title = t("app_title")
    page.window.width = 1000
    page.window.height = 820
    page.padding = 24
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    logger = _build_logger()

    # --- state -------------------------------------------------------------
    selected_folders: list[Path] = []
    last_scan: Optional[_PostScanState] = None

    # --- controls ----------------------------------------------------------
    title = ft.Text(t("app_title"), size=24, weight=ft.FontWeight.BOLD)
    subtitle = ft.Text(t("subtitle"), size=14)

    # Forward-declared so the on_change closure can reference it.
    language_dropdown: ft.Dropdown

    def _language_changed(e: ft.ControlEvent) -> None:
        new_lang = getattr(e, "data", None) or language_dropdown.value
        if new_lang in SUPPORTED_LANGUAGES:
            t.set_language(new_lang)

    language_dropdown = ft.Dropdown(
        value=t.language,
        options=[
            ft.DropdownOption(key="en", text=t("language_en")),
            ft.DropdownOption(key="nl", text=t("language_nl")),
        ],
        width=160,
        label=t("language_label"),
        enable_search=False,
        on_select=_language_changed,
    )

    folders_header = ft.Text(t("selected_folders"), weight=ft.FontWeight.BOLD)
    folders_list = ft.Column(spacing=4)
    folders_card = ft.Container(
        content=ft.Column([folders_header, folders_list]),
        padding=12,
        bgcolor=ft.Colors.GREY_100,
        border_radius=8,
    )

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    progress_bar = ft.ProgressBar(value=0, width=600, visible=False)
    progress_label = ft.Text("", size=12, visible=False)

    counts_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD)

    map_placeholder_text = ft.Text(t("map_placeholder"), color=ft.Colors.GREY_600)
    map_placeholder = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.MAP_OUTLINED, size=48, color=ft.Colors.GREY_400),
                map_placeholder_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        height=420,
        bgcolor=ft.Colors.GREY_100,
        border_radius=8,
        alignment=ft.Alignment.CENTER,
    )
    map_container = ft.Container(
        content=map_placeholder,
        height=420,
        border_radius=8,
        border=ft.Border.all(1, ft.Colors.GREY_300),
    )

    open_map_btn = ft.ElevatedButton(
        content=t("open_map_in_browser"),
        icon=ft.Icons.MAP,
        disabled=True,
        height=48,
    )
    pick_btn = ft.ElevatedButton(
        content=t("add_folder"),
        icon=ft.Icons.FOLDER_OPEN,
        height=48,
    )
    scan_btn = ft.FilledButton(
        content=t("scan"),
        icon=ft.Icons.SEARCH,
        disabled=True,
        height=48,
    )
    recursive_checkbox = ft.Checkbox(
        label=t("include_subfolders"),
        value=True,
    )

    status_text = ft.Text("", size=13, color=ft.Colors.GREY_700)

    # --- helpers -----------------------------------------------------------
    def refresh_folders_view() -> None:
        folders_list.controls.clear()
        if not selected_folders:
            folders_list.controls.append(
                ft.Text(t("no_folders_yet"), italic=True, color=ft.Colors.GREY_600))
        else:
            for folder in selected_folders:
                folders_list.controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.AMBER_700),
                        ft.Text(str(folder), expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            tooltip=t("remove"),
                            icon_size=16,
                            on_click=lambda e, f=folder: remove_folder(f),
                        ),
                    ], spacing=8)
                )
        scan_btn.disabled = len(selected_folders) == 0
        page.update()

    def render_post_scan_text() -> None:
        """Re-render counts + status from `last_scan`. Safe to call on lang change."""
        if last_scan is None:
            return
        if last_scan.error_message is not None:
            counts_text.value = ""
            status_text.value = t("error_prefix", message=last_scan.error_message)
            return
        counts_text.value = t(
            "scanned_summary",
            scanned=last_scan.scanned,
            with_gps=last_scan.with_gps,
        )
        if last_scan.map_path is not None:
            status_text.value = t("map_saved_to", path=last_scan.map_path)
        else:
            status_text.value = t("no_gps_found")

    def apply_translations() -> None:
        """Refresh every visible string after a language change."""
        page.title = t("app_title")
        title.value = t("app_title")
        subtitle.value = t("subtitle")
        folders_header.value = t("selected_folders")
        map_placeholder_text.value = t("map_placeholder")
        # Buttons: wrap the label in a Text control so reassignment is reliable.
        open_map_btn.content = ft.Text(t("open_map_in_browser"))
        pick_btn.content = ft.Text(t("add_folder"))
        scan_btn.content = ft.Text(t("scan"))
        recursive_checkbox.label = t("include_subfolders")
        language_dropdown.label = t("language_label")
        for opt in language_dropdown.options:
            opt.text = t(f"language_{opt.key}")
        render_post_scan_text()
        refresh_folders_view()  # rebuilds the folder list with translated labels
        page.update()

    t.on_change(apply_translations)


    def remove_folder(folder: Path) -> None:
        if folder in selected_folders:
            selected_folders.remove(folder)
        refresh_folders_view()

    async def pick_folder_clicked(_: ft.ControlEvent) -> None:
        result = await file_picker.get_directory_path(dialog_title=t("choose_folder_dialog"))
        if result:
            path = Path(result).resolve()
            if path not in selected_folders and path.is_dir():
                selected_folders.append(path)
                refresh_folders_view()

    def run_scan_blocking() -> None:
        """Runs in a worker thread so the UI stays responsive."""
        nonlocal last_scan

        try:
            def on_progress(i: int, total: int, name: str) -> None:
                if total > 0:
                    progress_bar.value = i / total
                progress_label.value = t(
                    "scanning_progress",
                    i=i, total=total, name=os.path.basename(name),
                )
                page.update()

            result = scan_directories(
                selected_folders,
                logger=logger,
                progress_callback=on_progress,
                recursive=bool(recursive_checkbox.value),
            )

            map_path: Optional[str] = None
            if result.files_with_gps > 0:
                preferred = selected_folders[0] / DEFAULT_OUTPUT_NAME
                try:
                    map_path = plot_map(result.dataframe, str(preferred), logger=logger)
                except OSError:
                    fallback = Path(tempfile.gettempdir()) / DEFAULT_OUTPUT_NAME
                    map_path = plot_map(result.dataframe, str(fallback), logger=logger)
                try:
                    map_container.content = build_map_control(result.dataframe)
                except Exception as map_exc:
                    logger.exception("Failed to build embedded map")
                    map_container.content = ft.Container(
                        content=ft.Text(
                            t("embedded_map_error", message=str(map_exc)),
                            color=ft.Colors.RED_700),
                        alignment=ft.Alignment.CENTER,
                    )
                open_map_btn.disabled = False
            else:
                open_map_btn.disabled = True
                map_container.content = map_placeholder

            last_scan = _PostScanState(
                scanned=result.files_scanned,
                with_gps=result.files_with_gps,
                map_path=map_path,
            )
            render_post_scan_text()

        except Exception as exc:
            logger.exception("Scan failed")
            last_scan = _PostScanState(
                scanned=0, with_gps=0, map_path=None, error_message=str(exc))
            render_post_scan_text()
        finally:
            progress_bar.visible = False
            progress_label.visible = False
            scan_btn.disabled = len(selected_folders) == 0
            pick_btn.disabled = False
            page.update()

    def scan_clicked(_: ft.ControlEvent) -> None:
        if not selected_folders:
            return
        progress_bar.value = 0
        progress_bar.visible = True
        progress_label.value = t("starting")
        progress_label.visible = True
        counts_text.value = ""
        status_text.value = ""
        open_map_btn.disabled = True
        scan_btn.disabled = True
        pick_btn.disabled = True
        page.update()
        page.run_thread(run_scan_blocking)

    def open_map_clicked(_: ft.ControlEvent) -> None:
        if last_scan and last_scan.map_path:
            webbrowser.open(f"file://{last_scan.map_path}")

    pick_btn.on_click = pick_folder_clicked
    scan_btn.on_click = scan_clicked
    open_map_btn.on_click = open_map_clicked

    # --- layout ------------------------------------------------------------
    header_row = ft.Row(
        [
            ft.Column([title, subtitle], expand=True, spacing=4),
            language_dropdown,
        ],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    page.add(
        header_row,
        ft.Divider(height=24),
        folders_card,
        ft.Row([pick_btn, scan_btn, recursive_checkbox], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Divider(height=24),
        progress_bar,
        progress_label,
        counts_text,
        map_container,
        ft.Row([open_map_btn], alignment=ft.MainAxisAlignment.END),
        status_text,
    )

    refresh_folders_view()


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
