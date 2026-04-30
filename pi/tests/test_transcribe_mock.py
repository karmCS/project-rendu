from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config import DEV_MODE, UNSYNCED_DIR
from services.transcribe import _TranscriptionWorker


def test_dev_mode_is_active():
    assert DEV_MODE, "Tests assume DEV_MODE=True (run on Windows or with RENDU_DEV=1)"


def test_worker_writes_txt_file_in_dev_mode(tmp_path):
    filename = "2026-01-01_10-00-00"
    audio_path = tmp_path / f"{filename}.wav"
    audio_path.write_bytes(b"RIFF" + b"\x00" * 36)

    transcript_path = UNSYNCED_DIR / f"{filename}.txt"
    if transcript_path.exists():
        transcript_path.unlink()

    finished = {}
    worker = _TranscriptionWorker(42, audio_path, filename)
    worker.finished.connect(lambda rid, p: finished.update({"id": rid, "path": p}))
    worker.failed.connect(lambda rid, e: finished.update({"error": e}))

    worker.run()  # synchronous call — DEV_MODE just sleeps + writes

    assert "error" not in finished, f"Should not fail: {finished.get('error')}"
    assert finished.get("id") == 42
    assert Path(finished["path"]).exists()
    content = Path(finished["path"]).read_text(encoding="utf-8")
    assert len(content) > 10


def test_worker_emits_finished_signal_with_correct_id(tmp_path):
    filename = "2026-01-01_12-00-00"
    audio_path = tmp_path / f"{filename}.wav"
    audio_path.write_bytes(b"")

    emitted_ids = []
    worker = _TranscriptionWorker(99, audio_path, filename)
    worker.finished.connect(lambda rid, _: emitted_ids.append(rid))

    worker.run()

    assert emitted_ids == [99]


def test_transcription_service_on_finished_updates_db(tmp_path):
    """_on_finished should update DB status and emit transcriptionComplete."""
    import database

    with patch("database.DB_PATH", tmp_path / "test.db"):
        database.init_db()
        filename = "2026-01-01_13-00-00"
        audio_path = tmp_path / f"{filename}.wav"
        audio_path.write_bytes(b"")
        rec_id = database.insert_recording(filename, filename, str(audio_path), 10)

        transcript_path = tmp_path / f"{filename}.txt"
        transcript_path.write_text("transcript", encoding="utf-8")

        mock_signals = MagicMock()
        from services.transcribe import TranscriptionService

        svc = TranscriptionService(mock_signals)
        svc._on_finished(rec_id, str(transcript_path))

        rec = database.get_recording(rec_id)
        assert rec.status == "unsynced"
        assert rec.transcript_path == str(transcript_path)
        mock_signals.transcriptionComplete.emit.assert_called_once_with(rec_id)


def test_transcription_service_on_failed_still_sets_unsynced(tmp_path):
    import database

    with patch("database.DB_PATH", tmp_path / "test.db"):
        database.init_db()
        filename = "2026-01-01_14-00-00"
        audio_path = tmp_path / f"{filename}.wav"
        audio_path.write_bytes(b"")
        rec_id = database.insert_recording(filename, filename, str(audio_path), 10)

        mock_signals = MagicMock()
        from services.transcribe import TranscriptionService

        svc = TranscriptionService(mock_signals)
        with patch("services.transcribe.UNSYNCED_DIR", tmp_path):
            svc._on_failed(rec_id, "Whisper timed out")

        rec = database.get_recording(rec_id)
        assert rec.status == "unsynced"
        mock_signals.transcriptionFailed.emit.assert_called_once_with(rec_id, "Whisper timed out")
