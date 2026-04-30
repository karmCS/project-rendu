# Rendu - Frontend Integration Guide

## Context

The React UI was designed in Claude Design and is being connected to the FastAPI backend. This doc covers how to wire the fetch calls, configure the base URL, and handle the key behaviors the UI depends on.

---

## Base URL Configuration

All API calls use an environment variable so the Ally's IP can be changed without touching code.

In your `.env` file:
```
VITE_API_BASE_URL=http://192.168.1.100:8000
```

In code:
```js
const API = import.meta.env.VITE_API_BASE_URL;
```

Default fallback for local dev: `http://localhost:8000`

---

## Kanban Data Flow

The kanban board fetches all notes from `GET /notes` and buckets them by `status`:

| Status value | Kanban column |
|---|---|
| `unsynced` | Unsynced |
| `processing` | Processing |
| `ready` | Ready to Review |
| `done` | Done |

**Auto-refresh:** Poll `GET /notes` every 10 seconds so Processing cards flip to Ready automatically.

```js
useEffect(() => {
  const interval = setInterval(fetchNotes, 10000);
  return () => clearInterval(interval);
}, []);
```

---

## Note Card Data

Each card displays:
- `recorded_at` - format as "Jan 15, 2024 · 9:32 AM"
- `duration_seconds` - format as "4m 32s"
- `template_name` - show as a small badge
- `processed_note_preview` - first ~120 chars, muted text, truncated with ellipsis

---

## Note Detail View

Fetch on card click: `GET /notes/{id}`

### Audio Player
Point the `<audio>` element's `src` at:
```
{API}/notes/{id}/audio
```
This streams the .wav directly. Standard HTML5 audio element works - no special handling needed.

### Raw Transcript
Collapsible section. Collapsed by default. Shows `raw_transcript` field.

### Processed Note
Editable `<textarea>` populated with `processed_note`. Edits are local - the user copies the edited text to clipboard. Changes are NOT saved back to the server (human edits before pasting into Epic).

### Template Selector + Reprocess
Populate the dropdown from `GET /templates`.

When user changes template and clicks Reprocess:
```
POST /notes/{id}/reprocess
Body: { "template_id": selectedTemplateId }
```
Show a loading state while processing. On success, update the textarea with the new `processed_note`.

### Copy to Clipboard
Copy the current textarea content (may be edited by user).
Show "Copied!" confirmation for 2 seconds.

### Mark as Done
```
PATCH /notes/{id}/status
Body: { "status": "done" }
```
On success, navigate back to kanban. The card will appear in Done column on next fetch.

---

## Templates Manager

### Load templates
```
GET /templates
```

### Create
```
POST /templates
Body: { name, format_type, template_text, is_default }
```

### Update
```
PUT /templates/{id}
Body: { name, format_type, template_text, is_default }
```

### Delete
```
DELETE /templates/{id}
```
Show a confirmation before deleting.

### is_default behavior
Only one template can be default. When the user toggles `is_default` on a template and saves, the backend handles unsetting the others. The frontend just sends whatever the user set.

---

## Error Handling

Keep errors non-alarming. Use simple inline messages:

- Network/connection error: `"Could not connect to server. Make sure the Ally is on."`
- 404: `"Note not found."`
- 500: `"Something went wrong. Try again."`

No toast libraries needed - a simple error state in the component is fine.

---

## Loading States

Use a spinner in Blue Grey (`#7298C7`) for:
- Initial kanban load
- Reprocess in progress
- Template save/delete

Processing cards in the kanban get a pulse animation (CSS only is fine).

---

## No Auth

No login, no tokens, no session management. The app is local-network only.
