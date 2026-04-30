import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from config import DB_PATH, STATUS_TRANSCRIBING


@dataclass(frozen=True)
class Recording:
    id: int
    filename: str
    label: str
    recorded_at: Optional[datetime]
    duration_seconds: int
    status: str
    transcript_path: Optional[str]
    audio_path: str
    created_at: datetime
    synced_at: Optional[datetime]


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _row_to_recording(row: sqlite3.Row) -> Recording:
    return Recording(
        id=row["id"],
        filename=row["filename"],
        label=row["label"] or row["filename"],
        recorded_at=_parse_dt(row["recorded_at"]),
        duration_seconds=row["duration_seconds"] or 0,
        status=row["status"],
        transcript_path=row["transcript_path"],
        audio_path=row["audio_path"],
        created_at=_parse_dt(row["created_at"]) or datetime.now(),
        synced_at=_parse_dt(row["synced_at"]),
    )


@contextmanager
def _db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with _db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                label TEXT,
                recorded_at TEXT,
                duration_seconds INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'transcribing',
                transcript_path TEXT,
                audio_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                synced_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON recordings(status)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_recorded_at ON recordings(recorded_at)"
        )
        conn.commit()


def insert_recording(
    filename: str,
    label: str,
    audio_path: str,
    duration_seconds: int,
    status: str = STATUS_TRANSCRIBING,
) -> int:
    with _db() as conn:
        cursor = conn.execute(
            """INSERT INTO recordings (filename, label, audio_path, duration_seconds, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filename, label, audio_path, duration_seconds, status, datetime.now().isoformat()),
        )
        return cursor.lastrowid


def update_status(recording_id: int, status: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE recordings SET status = ? WHERE id = ?", (status, recording_id)
        )


def update_transcript_path(recording_id: int, path: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE recordings SET transcript_path = ? WHERE id = ?", (path, recording_id)
        )


def update_audio_path(recording_id: int, path: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE recordings SET audio_path = ? WHERE id = ?", (path, recording_id)
        )


def update_label(recording_id: int, label: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE recordings SET label = ? WHERE id = ?", (label, recording_id)
        )


def mark_synced(recording_id: int, synced_at: datetime) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE recordings SET status = 'synced', synced_at = ? WHERE id = ?",
            (synced_at.isoformat(), recording_id),
        )


def list_recordings() -> list[Recording]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM recordings ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_recording(r) for r in rows]


def list_unsynced() -> list[Recording]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM recordings WHERE status IN ('unsynced', 'sync_failed')"
            " ORDER BY created_at ASC"
        ).fetchall()
        return [_row_to_recording(r) for r in rows]


def get_recording(recording_id: int) -> Optional[Recording]:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM recordings WHERE id = ?", (recording_id,)
        ).fetchone()
        return _row_to_recording(row) if row else None


def delete_recording(recording_id: int) -> Optional[Recording]:
    rec = get_recording(recording_id)
    if rec is None:
        return None
    with _db() as conn:
        conn.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
    return rec


def last_synced_at() -> Optional[datetime]:
    with _db() as conn:
        row = conn.execute(
            "SELECT synced_at FROM recordings WHERE synced_at IS NOT NULL"
            " ORDER BY synced_at DESC LIMIT 1"
        ).fetchone()
        return _parse_dt(row["synced_at"]) if row else None
