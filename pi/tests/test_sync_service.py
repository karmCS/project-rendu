from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import requests_mock as req_mock

from database import Recording
from services.sync_service import sync_one


def _make_recording(tmp_path: Path, status: str = "unsynced") -> Recording:
    wav = tmp_path / "2026-01-01_10-00-00.wav"
    txt = tmp_path / "2026-01-01_10-00-00.txt"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    txt.write_text("Patient presents with...", encoding="utf-8")
    return Recording(
        id=1,
        filename="2026-01-01_10-00-00",
        label="Room 3",
        recorded_at=datetime(2026, 1, 1, 10, 0, 0),
        duration_seconds=120,
        status=status,
        transcript_path=str(txt),
        audio_path=str(wav),
        created_at=datetime.now(),
        synced_at=None,
    )


def test_sync_one_success(tmp_path):
    rec = _make_recording(tmp_path)
    with req_mock.Mocker() as m:
        m.post("http://localhost:8000/sync", json={"id": 1, "status": "processing"})
        ok, msg = sync_one(rec)
    assert ok is True
    assert msg == "sent"


def test_sync_one_http_error(tmp_path):
    rec = _make_recording(tmp_path)
    with req_mock.Mocker() as m:
        m.post("http://localhost:8000/sync", status_code=500, text="Internal Server Error")
        ok, msg = sync_one(rec)
    assert ok is False
    assert "500" in msg


def test_sync_one_connection_error(tmp_path):
    rec = _make_recording(tmp_path)
    with req_mock.Mocker() as m:
        m.post("http://localhost:8000/sync", exc=Exception("connection refused"))
        ok, msg = sync_one(rec)
    assert ok is False


def test_sync_one_missing_transcript_creates_empty(tmp_path):
    wav = tmp_path / "2026-01-01_10-00-00.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    rec = Recording(
        id=1,
        filename="2026-01-01_10-00-00",
        label="Test",
        recorded_at=None,
        duration_seconds=60,
        status="unsynced",
        transcript_path=None,
        audio_path=str(wav),
        created_at=datetime.now(),
        synced_at=None,
    )
    with req_mock.Mocker() as m:
        m.post("http://localhost:8000/sync", json={"id": 2, "status": "processing"})
        ok, msg = sync_one(rec)
    assert ok is True


def test_sync_one_sends_correct_fields(tmp_path):
    rec = _make_recording(tmp_path)
    captured = {}
    with req_mock.Mocker() as m:
        def capture(request, context):
            captured["body"] = request.text
            context.status_code = 200
            return {"id": 1, "status": "processing"}
        m.post("http://localhost:8000/sync", json=capture)
        sync_one(rec)
    # Multipart body should contain filename and label
    assert "2026-01-01_10-00-00" in captured.get("body", "")
    assert "Room 3" in captured.get("body", "")
