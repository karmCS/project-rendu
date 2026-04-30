"""Read/write settings.json with safe defaults.

The file is read at call time (not cached at startup) so changes take
effect on the next operation without a server restart.
"""

import json
import os
from typing import Any

SETTINGS_FILE = "settings.json"

DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_AUDIO_PATH = os.path.join("storage", "audio")
DEFAULT_TRANSCRIPT_PATH = os.path.join("storage", "transcripts")

DEFAULTS: dict[str, str] = {
    "ollama_endpoint": DEFAULT_OLLAMA_ENDPOINT,
    "audio_storage_path": DEFAULT_AUDIO_PATH,
    "transcript_storage_path": DEFAULT_TRANSCRIPT_PATH,
}


def load_settings() -> dict[str, str]:
    """Return current settings, falling back to defaults for missing keys."""
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return {key: data.get(key, default) for key, default in DEFAULTS.items()}


def save_settings(values: dict[str, Any]) -> dict[str, str]:
    """Write the full settings object to settings.json and return it."""
    merged = load_settings()
    for key in DEFAULTS:
        if key in values and values[key] is not None:
            merged[key] = values[key]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)
    return merged


def get_ollama_endpoint() -> str:
    return load_settings()["ollama_endpoint"]


def get_audio_path() -> str:
    return load_settings()["audio_storage_path"]


def get_transcript_path() -> str:
    return load_settings()["transcript_storage_path"]
