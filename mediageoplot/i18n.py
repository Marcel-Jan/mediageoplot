"""Lightweight translation table for the GUI.

Usage:
    from .i18n import Translator
    t = Translator("en")
    t("app_title")           # -> "MediaMap — photo & video locations"
    t.set_language("nl")
    t("app_title")           # -> "MediaMap — foto- en videolocaties"
    t("scanned_summary", scanned=10, with_gps=3)
"""

from __future__ import annotations

from typing import Callable


SUPPORTED_LANGUAGES = ("en", "nl")
DEFAULT_LANGUAGE = "en"


_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "MediaMap — photo & video locations",
        "subtitle": (
            "Choose one or more folders containing your photos and videos. "
            "The app will scan them and show their locations on a map."
        ),
        "selected_folders": "Selected folders:",
        "no_folders_yet": "(none yet)",
        "add_folder": "Add a folder…",
        "scan": "Scan for locations",
        "include_subfolders": "Include subfolders",
        "remove": "Remove",
        "choose_folder_dialog": "Choose a folder",
        "starting": "Starting…",
        "scanning_progress": "Scanning {i} / {total}: {name}",
        "scanned_summary": "Scanned {scanned} files. {with_gps} had location info.",
        "open_map_in_browser": "Open map in browser",
        "map_saved_to": "Map saved to: {path}",
        "no_gps_found": "No files with GPS data were found, so no map was created.",
        "error_prefix": "Error: {message}",
        "map_placeholder": "The map will appear here after a scan.",
        "embedded_map_error": "Could not show the embedded map: {message}",
        "language_label": "Language",
        "language_en": "English",
        "language_nl": "Nederlands",
    },
    "nl": {
        "app_title": "MediaMap — foto- en videolocaties",
        "subtitle": (
            "Kies een of meer mappen met foto's en video's. "
            "De app scant ze en toont hun locaties op een kaart."
        ),
        "selected_folders": "Geselecteerde mappen:",
        "no_folders_yet": "(nog geen)",
        "add_folder": "Map toevoegen…",
        "scan": "Scan op locaties",
        "include_subfolders": "Inclusief submappen",
        "remove": "Verwijderen",
        "choose_folder_dialog": "Kies een map",
        "starting": "Starten…",
        "scanning_progress": "Bezig met {i} / {total}: {name}",
        "scanned_summary": "{scanned} bestanden gescand. {with_gps} hadden locatiegegevens.",
        "open_map_in_browser": "Open kaart in browser",
        "map_saved_to": "Kaart opgeslagen in: {path}",
        "no_gps_found": "Geen bestanden met GPS-gegevens gevonden, dus er is geen kaart gemaakt.",
        "error_prefix": "Fout: {message}",
        "map_placeholder": "De kaart verschijnt hier na een scan.",
        "embedded_map_error": "Kan de ingebedde kaart niet tonen: {message}",
        "language_label": "Taal",
        "language_en": "English",
        "language_nl": "Nederlands",
    },
}


class Translator:
    """Looks up strings in the active language; falls back to English."""

    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self._language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        self._listeners: list[Callable[[], None]] = []

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES or language == self._language:
            return
        self._language = language
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                pass

    def on_change(self, listener: Callable[[], None]) -> None:
        """Register a callback fired whenever the active language changes."""
        self._listeners.append(listener)

    def __call__(self, key: str, **fmt_kwargs) -> str:
        table = _STRINGS.get(self._language, _STRINGS[DEFAULT_LANGUAGE])
        template = table.get(key) or _STRINGS[DEFAULT_LANGUAGE].get(key) or key
        if fmt_kwargs:
            try:
                return template.format(**fmt_kwargs)
            except (KeyError, IndexError):
                return template
        return template
