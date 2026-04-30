# Rendu - Data Model & API Reference

## SQLite Schema

### Table: `notes`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto increment |
| filename | TEXT | Original filename from Pi (e.g. `2024-01-15_09-32-00`) |
| recorded_at | DATETIME | Parsed from filename |
| duration_seconds | INTEGER | Length of recording in seconds |
| raw_transcript | TEXT | Raw Whisper.cpp output |
| processed_note | TEXT | Ollama formatted output |
| template_id | INTEGER | FK → templates.id |
| status | TEXT | `unsynced` / `processing` / `ready` / `done` |
| audio_path | TEXT | Absolute path to .wav on Ally |
| created_at | DATETIME | When synced to Ally |
| processed_at | DATETIME | When Ollama finished |
| reviewed_at | DATETIME | When marked as done |

### Table: `templates`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto increment |
| name | TEXT | Display name, e.g. "Epic Follow Up" |
| format_type | TEXT | `epic` / `soap` / `dap` / `progress` / `custom` |
| template_text | TEXT | The structure Ollama formats into |
| is_default | BOOLEAN | Only one should be true at a time |
| created_at | DATETIME | |
| updated_at | DATETIME | |

---

## Default Template Content (seed on first run)

### Epic Follow Up (`epic`, is_default=False)
```
Visit Type: Follow Up
Date:
Provider:

Subjective:

Objective:

Assessment:

Plan:
```

### Epic New Patient (`epic`, is_default=False)
```
Visit Type: New Patient
Date:
Provider:

Chief Complaint:

History of Present Illness:

Past Medical History:

Medications:

Allergies:

Review of Systems:

Physical Exam:

Assessment:

Plan:
```

### SOAP Note (`soap`, is_default=True)
```
Subjective:

Objective:

Assessment:

Plan:
```

### DAP Note (`dap`, is_default=False)
```
Data:

Assessment:

Plan:
```

---

## API Routes

### POST `/sync`
Receives audio (.wav) and transcript (.txt) files from the Pi.

**Request:** `multipart/form-data`
- `audio_file`: .wav file
- `transcript_file`: .txt file
- `filename`: base filename (e.g. `2024-01-15_09-32-00`)
- `duration_seconds`: integer

**Behavior:**
1. Save .wav to `storage/audio/{filename}.wav`
2. Save .txt to `storage/transcripts/{filename}.txt`
3. Create SQLite record with status `processing`
4. Fire-and-forget: call Ollama with transcript + default template
5. On Ollama success: update record with `processed_note`, status → `ready`, set `processed_at`
6. On Ollama failure: status → `unsynced` (so it can be retried)

**Response:** `{"id": 42, "status": "processing"}`

---

### GET `/notes`
Returns all notes for the kanban board, ordered by `recorded_at` descending.

**Response:**
```json
[
  {
    "id": 1,
    "filename": "2024-01-15_09-32-00",
    "recorded_at": "2024-01-15T09:32:00",
    "duration_seconds": 272,
    "status": "ready",
    "template_id": 1,
    "template_name": "SOAP Note",
    "processed_note_preview": "Subjective: Patient presents with..."
  }
]
```

`processed_note_preview` is the first 120 characters of `processed_note`.

---

### GET `/notes/{id}`
Returns full note detail.

**Response:**
```json
{
  "id": 1,
  "filename": "2024-01-15_09-32-00",
  "recorded_at": "2024-01-15T09:32:00",
  "duration_seconds": 272,
  "raw_transcript": "...",
  "processed_note": "...",
  "status": "ready",
  "template_id": 1,
  "template_name": "SOAP Note",
  "created_at": "...",
  "processed_at": "..."
}
```

---

### PATCH `/notes/{id}/status`
Updates note status.

**Request:** `{"status": "done"}`

**Behavior:** Also sets `reviewed_at` when status is set to `done`.

**Response:** Updated note object.

---

### DELETE `/notes/{id}`
Deletes the note record and its associated files from disk.

**Response:** `{"deleted": true}`

---

### GET `/notes/{id}/audio`
Streams the .wav file for browser audio playback.

Use `FileResponse` with media type `audio/wav`. Must support HTTP range requests for the browser audio player scrubber to work.

```python
from fastapi.responses import FileResponse
return FileResponse(audio_path, media_type="audio/wav")
```

---

### POST `/notes/{id}/reprocess`
Re-runs Ollama on an existing note with a different template.

**Request:** `{"template_id": 3}`

**Behavior:**
1. Set status → `processing`
2. Run Ollama with existing `raw_transcript` + new template
3. Update `processed_note`, `template_id`, status → `ready`, `processed_at`

**Response:** Updated note object.

---

### GET `/templates`
Returns all templates.

**Response:**
```json
[
  {
    "id": 1,
    "name": "SOAP Note",
    "format_type": "soap",
    "template_text": "Subjective:\n\nObjective:\n\nAssessment:\n\nPlan:",
    "is_default": true,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### POST `/templates`
Creates a new template.

**Request:**
```json
{
  "name": "My Custom Note",
  "format_type": "custom",
  "template_text": "...",
  "is_default": false
}
```

**Behavior:** If `is_default: true`, unset `is_default` on all other templates first.

**Response:** Created template object.

---

### PUT `/templates/{id}`
Updates an existing template.

**Request:** Same shape as POST.

**Behavior:** If `is_default: true`, unset all others first. Update `updated_at`.

**Response:** Updated template object.

---

### DELETE `/templates/{id}`
Deletes a template. Do not allow deletion if it's the only template remaining.

**Response:** `{"deleted": true}`
