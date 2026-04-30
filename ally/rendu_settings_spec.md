# Rendu - Settings Page Spec

## Overview

The Settings page lives at `/settings` in the React UI. It surfaces configuration and system state that the user may need to adjust at deployment time or during ongoing use. There is no authentication - settings are saved directly to a `settings.json` file in the project root.

---

## `settings.json` - Structure & Defaults

Created automatically on first run if it does not exist. Backend reads this file at call time (not at startup), so changes take effect on the next operation without a restart.

```json
{
  "ollama_endpoint": "http://localhost:11434",
  "audio_storage_path": "storage/audio",
  "transcript_storage_path": "storage/transcripts"
}
```

If `settings.json` is missing or a key is absent, the backend falls back to these defaults.

---

## New API Routes

### `GET /settings`
Returns current settings plus live system stats.

**Response:**
```json
{
  "ollama_endpoint": "http://localhost:11434",
  "audio_storage_path": "storage/audio",
  "transcript_storage_path": "storage/transcripts",
  "audio_size_mb": 142.3,
  "transcript_size_mb": 0.8,
  "database_size_mb": 1.2,
  "total_notes": 38,
  "last_synced_at": "2024-01-15T09:32:00",
  "python_version": "3.11.4",
  "fastapi_version": "0.111.0"
}
```

`last_synced_at` is the most recent `created_at` value in the `notes` table. Returns `null` if no notes exist yet.

---

### `PUT /settings`
Saves updated settings to `settings.json`.

**Request:**
```json
{
  "ollama_endpoint": "http://192.168.1.50:11434",
  "audio_storage_path": "storage/audio",
  "transcript_storage_path": "storage/transcripts"
}
```

**Behavior:**
- Validate that `ollama_endpoint` is a well-formed URL
- Validate that storage paths exist on disk; return a clear error if they do not
- Write the full settings object to `settings.json`
- Storage path changes take effect on the next file operation - no restart required

**Response:** Updated settings object (same shape as `GET /settings`).

---

### `POST /settings/purge-done`
Deletes audio and transcript files for all notes with `status = 'done'`. Does **not** delete the database records.

**Response:**
```json
{
  "purged_count": 12,
  "space_reclaimed_mb": 98.4
}
```

If no done notes exist, returns `{ "purged_count": 0, "space_reclaimed_mb": 0 }`.

---

## `ollama_service.py` - Read Endpoint at Call Time

The Ollama endpoint must be read from `settings.json` on every call, not cached at startup. This ensures endpoint changes take effect immediately.

```python
import json, os

def get_ollama_endpoint() -> str:
    try:
        with open("settings.json") as f:
            return json.load(f).get("ollama_endpoint", "http://localhost:11434")
    except (FileNotFoundError, json.JSONDecodeError):
        return "http://localhost:11434"

async def run_ollama(transcript: str, template_text: str) -> str:
    endpoint = get_ollama_endpoint()
    # ... rest of function uses endpoint variable
```

---

## UI - Settings Page Layout

### Section: Inference

| Field | Input type | Notes |
|---|---|---|
| Ollama Endpoint URL | Text input | e.g. `http://localhost:11434` |

Save button below. On save, call `PUT /settings`. Show inline success or error message.

> **Why this matters:** If inference moves to a separate machine on the LAN, update this URL to point to the new host. No code changes needed.

---

### Section: Storage Paths

| Field | Input type | Notes |
|---|---|---|
| Audio Storage Path | Text input | Absolute or relative path |
| Transcript Storage Path | Text input | Absolute or relative path |

Shared Save button with Inference section, or a separate one - either is fine. Validate on the backend that the paths exist before saving.

---

### Section: Disk Usage

Display as read-only stat cards or a simple table. Fetched from `GET /settings`.

| Label | Value |
|---|---|
| Audio files | `142.3 MB` |
| Transcripts | `0.8 MB` |
| Database | `1.2 MB` |

**Purge Done Notes** button below disk usage stats.
- Show: `"This will delete audio and transcript files for all done notes. This cannot be undone."` in a confirmation dialog before firing
- On confirm: `POST /settings/purge-done`
- On success: show `"Purged 12 notes · 98.4 MB reclaimed"` inline

---

### Section: Sync

| Label | Value |
|---|---|
| Last Synced | `Jan 15, 2024 · 9:32 AM` (or `"No notes synced yet"`) |
| Pi Sync Target | `http://rendu-ally.local:8000/sync` (read-only, for reference) |

The Pi Sync Target is a static display showing the URL the Pi's sync script should be pointing to. Useful reminder during setup or when moving to a new network.

---

### Section: System Info

Read-only. Fetched from `GET /settings`.

| Label | Value |
|---|---|
| Total Notes | `38` |
| Python Version | `3.11.4` |
| FastAPI Version | `0.111.0` |

---

## Error Handling

Follow the same pattern as the rest of the app - inline, non-alarming messages:

| Scenario | Message |
|---|---|
| Invalid Ollama URL format | `"Please enter a valid URL (e.g. http://localhost:11434)"` |
| Storage path does not exist | `"Path not found on disk. Create it first or check the spelling."` |
| Cannot reach Ollama endpoint | `"Could not connect to Ollama at that address."` |
| Purge with no done notes | `"No done notes to purge."` |
| General save failure | `"Could not save settings. Check that the server is running."` |

---

## Loading States

Use the same Blue Grey (`#7298C7`) spinner used elsewhere in the app for:
- Initial page load (fetching `GET /settings`)
- Save in progress
- Purge in progress

---

## Notes for Claude Code

- `settings.json` lives in the project root alongside `main.py`
- The `GET /settings` route computes disk usage live using `os.path.getsize` / directory walk - do not cache it
- `python_version` via `sys.version`, `fastapi_version` via `importlib.metadata.version("fastapi")`
- The purge route should handle missing files gracefully (a file listed in the DB may have already been deleted manually)
- All settings routes must be registered **before** the static file mount in `main.py`
