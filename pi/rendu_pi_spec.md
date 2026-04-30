# Rendu - Pi UI Spec for Claude Code

## What You're Building

A PyQt5 touchscreen app that runs on a Raspberry Pi 5 with an official 7" touchscreen. It records patient encounter audio, transcribes it locally with Whisper.cpp, and syncs files to the ASUS ROG Ally over the home network.

No cloud. No physical keyboard. Everything is tap-based - text entry uses an in-app on-screen keyboard.

---

## Project Structure

```
rendu-pi/
  main.py                  # App entry point, screen router
  screens/
    record.py              # Record screen
    recordings.py          # Recordings list screen
    sync.py                # Sync screen
  services/
    audio.py               # PyAudio recording, pause/resume, waveform data
    transcribe.py          # Whisper.cpp subprocess wrapper
    sync_service.py        # HTTP POST to Ally
    storage.py             # File I/O, storage stats
  database.py              # SQLite via sqlite3 (no ORM needed)
  config.py                # Constants (paths, Ally URL, timeouts)
  recordings/
    unsynced/              # .wav + .txt files pending sync
    synced/                # .wav + .txt files successfully synced
  database.db              # Auto-created on first run
```

---

## Tech Stack

- **PyQt5** - UI framework
- **PyAudio** - audio capture and waveform data
- **sqlite3** - local database (stdlib, no install needed)
- **subprocess** - call Whisper.cpp binary
- **requests** - HTTP POST to Ally on sync
- **numpy** - waveform amplitude calculation from audio buffer

Install:
```bash
pip install PyQt5 pyaudio requests numpy
```

Whisper.cpp must be compiled separately on the Pi. Binary assumed at `/usr/local/bin/whisper-cpp`. Model assumed at `~/models/ggml-small.bin`.

---

## Display

- **Screen:** Official Raspberry Pi 7" Touchscreen
- **Resolution:** 800 × 480
- **Orientation:** Landscape
- **Input:** Touch only - no physical keyboard or mouse assumed; text entry via in-app `TouchKeyboard` widget
- **Minimum touch target:** 60px height, 120px width

---

## Auto-Start (Pi / Linux)

Create a systemd service or add to `/etc/xdg/autostart/`:

```ini
[Desktop Entry]
Type=Application
Name=Rendu
Exec=python3 /home/pi/rendu-pi/main.py
```

Or via systemd for reliability:

```ini
[Unit]
Description=Rendu Pi UI
After=graphical.target

[Service]
User=pi
WorkingDirectory=/home/pi/rendu-pi
ExecStart=python3 main.py
Restart=on-failure

[Install]
WantedBy=graphical.target
```

---

## Screen Management

Use a QStackedWidget as the root container. Three screens:

| Index | Screen |
|---|---|
| 0 | Record |
| 1 | Recordings List |
| 2 | Sync |

Navigation between screens via bottom tab bar (3 large tap targets, always visible).

---

## Screen Sleep / Wake

- **While recording:** Disable screen blanking entirely. Call `xset s off` and `xset -dpms` via subprocess on recording start. Re-enable on stop.
- **While idle:** Screen blanks after 15 minutes. Use `xset s 900` on app startup.
- **Wake on tap:** PyQt5 catches any touch event and calls `xset s reset` to wake. No action is taken from the wake tap itself - it only wakes the screen.

```python
# On app startup
import subprocess
subprocess.run(["xset", "s", "900"])   # 15 min idle timeout
subprocess.run(["xset", "+dpms"])

# On recording start
subprocess.run(["xset", "s", "off"])
subprocess.run(["xset", "-dpms"])

# On recording stop
subprocess.run(["xset", "s", "900"])
subprocess.run(["xset", "+dpms"])
```

---

## Config (`config.py`)

```python
ALLY_URL = "http://rendu-ally.local:8000"
RECORDINGS_DIR = "/home/pi/rendu-pi/recordings"
UNSYNCED_DIR = f"{RECORDINGS_DIR}/unsynced"
SYNCED_DIR = f"{RECORDINGS_DIR}/synced"
WHISPER_BIN = "/usr/local/bin/whisper-cpp"
WHISPER_MODEL = "/home/pi/models/ggml-small.bin"
DB_PATH = "/home/pi/rendu-pi/database.db"
IDLE_TIMEOUT_SECONDS = 900  # 15 minutes
```

---

## Local Database (`database.db`)

Single table: `recordings`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto increment |
| filename | TEXT | Base filename, e.g. `2024-01-15_09-32-00` |
| label | TEXT | User-provided label. Defaults to filename. |
| recorded_at | DATETIME | Parsed from filename |
| duration_seconds | INTEGER | Total recorded time (excluding paused time) |
| status | TEXT | `transcribing` / `unsynced` / `syncing` / `synced` / `sync_failed` |
| transcript_path | TEXT | Absolute path to .txt |
| audio_path | TEXT | Absolute path to .wav |
| created_at | DATETIME | When recording was stopped |
| synced_at | DATETIME | When successfully synced to Ally |

---

## Screen 1: Record

### Layout

```
┌─────────────────────────────────────┐
│  ● RECORDING   00:04:32        [■]  │  ← status bar (top)
│                                     │
│  ┌─────────────────────────────┐    │
│  │   ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~  │    │  ← live waveform
│  └─────────────────────────────┘    │
│                                     │
│         [ ⏸  PAUSE ]               │  ← pause button (visible while recording)
│                                     │
│         [  ● RECORD  ]             │  ← main action button
│                                     │
│  [  Recordings  ]  [  Sync  ]       │  ← bottom tab bar
└─────────────────────────────────────┘
```

### States

**Idle (not recording):**
- Main button: large red circle, label "RECORD"
- Pause button: hidden
- Status bar: empty
- Waveform: flat line

**Recording:**
- Main button: large gray square, label "STOP"
- Pause button: visible, label "PAUSE"
- Status bar: red dot + "RECORDING" + elapsed timer (counts up, HH:MM:SS)
- Waveform: live amplitude visualization, updates every 100ms
- Screen blanking disabled

**Paused:**
- Main button: large gray square, label "STOP"
- Pause button: label changes to "RESUME", amber color
- Status bar: amber dot + "PAUSED" + elapsed timer (frozen)
- Waveform: flat line (not recording audio)

### Behavior

**Record tap:**
- Generate filename from current datetime: `YYYY-MM-DD_HH-MM-SS`
- Open PyAudio stream, begin writing to temp .wav file
- Start elapsed timer
- Disable screen blanking

**Pause tap:**
- Stop writing audio to buffer (mute, do not record silence)
- Freeze elapsed timer
- Status → PAUSED

**Resume tap:**
- Resume writing audio to same .wav file (continuous stream, no gap)
- Resume elapsed timer from where it stopped
- Status → RECORDING

**Stop tap:**
- Close PyAudio stream
- Finalize .wav file to `recordings/unsynced/{filename}.wav`
- Create DB record with status `transcribing`, duration = total recorded seconds (pause time excluded)
- Re-enable screen blanking
- Navigate to Recordings List screen
- In background thread: run Whisper.cpp on the .wav file

### Recording Errors

The Record tap path wraps recorder construction and `start()` in a try/except. If PyAudio fails to initialise (no input device, microphone unplugged, exclusive lock held by another process), the screen:

1. Clears the in-progress recorder reference.
2. Deletes the empty `.wav` stub created at the target path, if any.
3. Shows a `QMessageBox.warning` titled "Microphone unavailable" with a short instruction to check the microphone and the underlying exception text.
4. Resets state to IDLE so the Record button is interactive again.

This guard only matters on the Pi; the DEV_MODE `MockAudioRecorder` cannot fail.

### Waveform

- Use PyAudio callback to read audio chunks
- Calculate RMS amplitude per chunk with numpy
- Draw as simple bar or line graph using QPainter
- Update every 100ms via QTimer
- Width: full screen width minus padding
- Height: ~100px
- Color: white bars/line on dark background

### Pause Implementation Note

Do not record silence during pause. Use a boolean flag in the PyAudio callback:

```python
self.paused = False

def audio_callback(self, in_data, frame_count, time_info, status):
    if not self.paused:
        self.wav_file.writeframes(in_data)
    return (in_data, pyaudio.paContinue)
```

This keeps the output as one seamless .wav file with no silence gaps and no stitching needed.

---

## Screen 2: Recordings List

### Layout

```
┌─────────────────────────────────────┐
│  Recordings              4.2 GB free│  ← header + storage indicator
│                                     │
│  ┌─────────────────────────────┐    │
│  │ Room 3 Follow Up    [READY] │    │
│  │ Jan 15 · 9:32 AM · 4m 32s  │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 2024-01-15_10-15-00  [SYNC FAILED]│
│  │ Jan 15 · 10:15 AM · 2m 10s │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ New Patient          [DONE] │    │
│  │ Jan 15 · 8:00 AM · 8m 05s  │    │
│  └─────────────────────────────┘    │
│                                     │
│  [ Record ]  [  Recordings  ]  [ Sync ]│
└─────────────────────────────────────┘
```

### Recording Card

Each card shows:
- **Label** (top left) - defaults to filename if not set
- **Status badge** (top right) - color-coded pill
- **Date and time** (bottom left) - formatted as "Jan 15 · 9:32 AM"
- **Duration** (bottom right) - formatted as "4m 32s"
- **Pencil button** (far right, rendered as a Unicode pencil character U+270E): tap to rename via on-screen keyboard

**Card gestures:**
- Quick tap → open detail sheet
- Long-press (≥ 500ms, < 10px movement) → open rename keyboard directly
- Drag (> 10px) → cancels long-press so list scrolling works

### Status Badge Colors

| Status | Badge | Color |
|---|---|---|
| `transcribing` | TRANSCRIBING | Blue + spinner |
| `unsynced` | READY | Green |
| `syncing` | SYNCING | Blue + spinner |
| `synced` | SYNCED | Gray |
| `sync_failed` | SYNC FAILED | Red |

### Storage Indicator

Top right of header. Show free space on the SD card partition.

```python
import shutil
free = shutil.disk_usage("/").free / (1024**3)
label = f"{free:.1f} GB free"
```

Update on screen load. Color: white if > 2GB, amber if 1–2GB, red if < 1GB.

### Tap a Card → Recording Detail Sheet

Slide up from bottom (or modal). Shows:

- Label field with **Edit** button - opens the in-app `TouchKeyboard` (`screens/touch_keyboard.py`) for renaming
- Date, duration, status
- **Delete** button (red) - confirm dialog before deleting. Removes DB record and files from disk.

### TouchKeyboard

A custom PyQt5 `QDialog` (`screens/touch_keyboard.py`) - frameless, full 800×480, providing a QWERTY layout, number row, sticky shift, backspace, space, and Cancel/Done. Used wherever text entry is needed on the Pi (rename from card pencil, long-press, or detail sheet). No system dependency on `matchbox-keyboard` or similar - works identically in DEV_MODE on Windows.

Static helper:
```python
text, ok = TouchKeyboard.get_text(parent, "Edit Label", initial_text)
```

### Transcription Progress

While status is `transcribing`, show a small spinner inside the badge and a line of muted text below the card: "Transcribing... this may take a few minutes."

No progress percentage - Whisper.cpp doesn't emit progress. Just spinner until done.

When Whisper finishes, update the DB record to `unsynced` and refresh the card in place.

---

## Screen 3: Sync

### Layout

```
┌─────────────────────────────────────┐
│  Sync to Ally                       │
│                                     │
│  3 recordings ready to sync         │
│                                     │
│        [  SYNC NOW  ]               │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  Last synced: Jan 15 at 2:34 PM     │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ Room 3 Follow Up   [sent]   │    │
│  │ New Patient        [failed] │    │
│  └─────────────────────────────┘    │
│                                     │
│  [ Record ]  [ Recordings ]  [ Sync ]│
└─────────────────────────────────────┘
```

### Behavior

**On screen load:**
- Count recordings with status `unsynced` or `sync_failed`
- Show "N recordings ready to sync" (or "Nothing to sync" if 0)
- Show last synced timestamp from DB (most recent `synced_at`)

**SYNC NOW tap:**
- Button label → "SYNCING..." + spinner, disabled
- For each `unsynced` or `sync_failed` recording:
  - Set status → `syncing`, refresh list
  - POST to `{ALLY_URL}/sync` with multipart:
    - `audio_file`: .wav
    - `transcript_file`: .txt
    - `filename`: base filename
    - `label`: label text
    - `duration_seconds`: integer
  - On HTTP 200: move files to `recordings/synced/`, set status → `synced`, set `synced_at`
  - On failure: set status → `sync_failed`
- After all files attempted: re-enable button, update summary

**Sync is sequential, not parallel.** One file at a time to avoid overwhelming the Ally.

**No automatic sync.** Manual trigger only. The user decides when to sync.

### Error Handling

If the Ally is unreachable (connection refused, timeout):
- Show inline message: "Could not reach the Ally. Make sure you're on your home network."
- All attempted files revert to `sync_failed`
- No crash, no alarm

---

## Whisper.cpp Transcription Service (`services/transcribe.py`)

Run as a background thread (not async - subprocess is blocking).

```python
import subprocess
import threading

def transcribe(filename: str, audio_path: str, on_complete, on_error):
    def run():
        try:
            result = subprocess.run(
                [
                    WHISPER_BIN,
                    "-m", WHISPER_MODEL,
                    "-f", audio_path,
                    "-otxt",
                    "-of", f"{UNSYNCED_DIR}/{filename}"
                ],
                capture_output=True,
                text=True,
                timeout=600  # 10 min max
            )
            if result.returncode == 0:
                on_complete(filename)
            else:
                on_error(filename, result.stderr)
        except subprocess.TimeoutExpired:
            on_error(filename, "Whisper timed out")
        except Exception as e:
            on_error(filename, str(e))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
```

Whisper.cpp `-otxt` flag writes `{filename}.txt` automatically. The transcript file will appear at `{UNSYNCED_DIR}/{filename}.txt`.

On `on_complete`: update DB status → `unsynced`, emit a Qt signal to refresh the Recordings List screen.

On `on_error`: update DB status → `unsynced` with a note, or add an `error_message` column - either way, don't silently fail. Show the card as READY so it can still be synced (raw transcript will be empty but the audio is intact).

---

## Sync Service Note

The `/sync` endpoint on the Ally already exists (defined in `rendu_data_model.md`). The Pi POSTs:
- `audio_file` (.wav)
- `transcript_file` (.txt)
- `filename`
- `duration_seconds`

Add `label` as an additional field. The Ally backend will need a minor update to accept and store it (update the `notes` table with a `label` column and accept it in the `/sync` route).

---

## Styling

Dark background throughout. High contrast for clinic lighting.

| Element | Value |
|---|---|
| Background | `#1a1a1a` |
| Card background | `#2a2a2a` |
| Primary text | `#ffffff` |
| Muted text | `#888888` |
| Record button | `#cc3333` (red) |
| Stop button | `#444444` (gray) |
| Pause button | `#e6a817` (amber) |
| Resume button | `#e6a817` (amber) |
| Sync button | `#2d6bbf` (blue) |
| Tab bar background | `#111111` |
| Active tab | `#ffffff` |
| Inactive tab | `#555555` |
| Waveform | `#7298C7` (Rendu blue) |

Font: System default. Minimum 16pt for all labels. Button labels 20pt bold.

---

## What Claude Code Should Build First

Tell Claude Code to build in this order:

1. `main.py` - QApplication, QStackedWidget, bottom tab bar, screen switching
2. `database.py` - create table, insert/update/query helpers
3. `config.py` - all constants
4. `screens/record.py` - Record screen with waveform, record/pause/resume/stop states
5. `services/audio.py` - PyAudio recording with pause support
6. `screens/recordings.py` - Recordings list, card component, storage indicator
7. `services/transcribe.py` - Whisper.cpp background thread
8. `screens/sync.py` - Sync screen, sequential sync loop
9. `services/sync_service.py` - HTTP POST logic
