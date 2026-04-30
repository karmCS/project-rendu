import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_db(tmp_path):
    db_file = tmp_path / "test.db"
    with patch("config.DB_PATH", db_file):
        import database
        # Re-run init with the patched path
        with patch("database.DB_PATH", db_file):
            database.init_db()
            yield database, db_file


def test_insert_and_list(tmp_db):
    db, _ = tmp_db
    with patch("database.DB_PATH", _):
        rec_id = db.insert_recording(
            filename="2026-01-01_10-00-00",
            label="Test",
            audio_path="/tmp/test.wav",
            duration_seconds=30,
        )
        assert rec_id == 1
        rows = db.list_recordings()
        assert len(rows) == 1
        assert rows[0].filename == "2026-01-01_10-00-00"
        assert rows[0].status == "transcribing"
        assert rows[0].duration_seconds == 30


def test_update_status(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        rec_id = db.insert_recording("2026-01-01_10-00-00", "T", "/tmp/t.wav", 10)
        db.update_status(rec_id, "unsynced")
        rec = db.get_recording(rec_id)
        assert rec.status == "unsynced"


def test_list_unsynced_filters(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        id1 = db.insert_recording("2026-01-01_10-00-00", "A", "/tmp/a.wav", 5)
        id2 = db.insert_recording("2026-01-01_10-00-01", "B", "/tmp/b.wav", 5)
        db.update_status(id1, "unsynced")
        db.update_status(id2, "synced")
        rows = db.list_unsynced()
        assert len(rows) == 1
        assert rows[0].id == id1


def test_mark_synced(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        rec_id = db.insert_recording("2026-01-01_10-00-00", "A", "/tmp/a.wav", 5)
        db.update_status(rec_id, "unsynced")
        now = datetime.now()
        db.mark_synced(rec_id, now)
        rec = db.get_recording(rec_id)
        assert rec.status == "synced"
        assert rec.synced_at is not None


def test_delete_recording(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        rec_id = db.insert_recording("2026-01-01_10-00-00", "A", "/tmp/a.wav", 5)
        assert db.get_recording(rec_id) is not None
        db.delete_recording(rec_id)
        assert db.get_recording(rec_id) is None
        assert db.list_recordings() == []


def test_update_label(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        rec_id = db.insert_recording("2026-01-01_10-00-00", "Old", "/tmp/a.wav", 5)
        db.update_label(rec_id, "New Label")
        rec = db.get_recording(rec_id)
        assert rec.label == "New Label"


def test_last_synced_at_none_when_empty(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        assert db.last_synced_at() is None


def test_last_synced_at_returns_most_recent(tmp_db):
    db, path = tmp_db
    with patch("database.DB_PATH", path):
        id1 = db.insert_recording("2026-01-01_10-00-00", "A", "/tmp/a.wav", 5)
        id2 = db.insert_recording("2026-01-01_11-00-00", "B", "/tmp/b.wav", 5)
        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 1, 11, 0, 0)
        db.mark_synced(id1, t1)
        db.mark_synced(id2, t2)
        result = db.last_synced_at()
        assert result is not None
        assert result >= t2
