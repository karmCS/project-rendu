from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from database import Recording
from services.storage import delete_recording_files, disk_free_gb, move_to_synced


def _make_recording(audio_path: str, transcript_path: str = None) -> Recording:
    return Recording(
        id=1,
        filename="2026-01-01_10-00-00",
        label="Test",
        recorded_at=datetime(2026, 1, 1, 10, 0, 0),
        duration_seconds=60,
        status="unsynced",
        transcript_path=transcript_path,
        audio_path=audio_path,
        created_at=datetime.now(),
        synced_at=None,
    )


def test_disk_free_gb_returns_positive(tmp_path):
    gb = disk_free_gb(tmp_path)
    assert gb > 0


def test_delete_recording_files_removes_both(tmp_path):
    wav = tmp_path / "test.wav"
    txt = tmp_path / "test.txt"
    wav.write_bytes(b"data")
    txt.write_text("transcript")
    rec = _make_recording(str(wav), str(txt))
    delete_recording_files(rec)
    assert not wav.exists()
    assert not txt.exists()


def test_delete_recording_files_tolerates_missing(tmp_path):
    rec = _make_recording("/nonexistent/path.wav", "/nonexistent/path.txt")
    delete_recording_files(rec)  # should not raise


def test_move_to_synced_moves_files(tmp_path):
    from config import SYNCED_DIR

    unsynced = tmp_path / "unsynced"
    synced = tmp_path / "synced"
    unsynced.mkdir()
    synced.mkdir()

    wav = unsynced / "2026-01-01_10-00-00.wav"
    txt = unsynced / "2026-01-01_10-00-00.txt"
    wav.write_bytes(b"audio data")
    txt.write_text("transcript", encoding="utf-8")

    rec = _make_recording(str(wav), str(txt))

    with patch("services.storage.SYNCED_DIR", synced), \
         patch("database.update_audio_path") as mock_audio, \
         patch("database.update_transcript_path") as mock_transcript:
        move_to_synced(rec)

    assert (synced / "2026-01-01_10-00-00.wav").exists()
    assert (synced / "2026-01-01_10-00-00.txt").exists()
    assert not wav.exists()
    assert not txt.exists()
    mock_audio.assert_called_once_with(1, str(synced / "2026-01-01_10-00-00.wav"))
    mock_transcript.assert_called_once_with(1, str(synced / "2026-01-01_10-00-00.txt"))


def test_move_to_synced_tolerates_missing_files(tmp_path):
    synced = tmp_path / "synced"
    synced.mkdir()
    rec = _make_recording("/nonexistent/path.wav", "/nonexistent/path.txt")
    with patch("services.storage.SYNCED_DIR", synced), \
         patch("database.update_audio_path"), \
         patch("database.update_transcript_path"):
        move_to_synced(rec)  # should not raise
