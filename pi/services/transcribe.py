import subprocess
import time
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

import database
from config import (
    DEV_MODE,
    STATUS_UNSYNCED,
    UNSYNCED_DIR,
    WHISPER_BIN,
    WHISPER_MOCK_DELAY_SECONDS,
    WHISPER_MOCK_TEXT,
    WHISPER_MODEL,
    WHISPER_TIMEOUT_SECONDS,
)


class _TranscriptionWorker(QObject):
    finished = pyqtSignal(int, str)
    failed = pyqtSignal(int, str)

    def __init__(self, recording_id: int, audio_path: Path, filename: str) -> None:
        super().__init__()
        self.recording_id = recording_id
        self.audio_path = audio_path
        self.filename = filename

    @pyqtSlot()
    def run(self) -> None:
        transcript_path = UNSYNCED_DIR / f"{self.filename}.txt"

        if DEV_MODE:
            time.sleep(WHISPER_MOCK_DELAY_SECONDS)
            transcript_path.write_text(WHISPER_MOCK_TEXT, encoding="utf-8")
            self.finished.emit(self.recording_id, str(transcript_path))
            return

        prefix = str(UNSYNCED_DIR / self.filename)
        try:
            result = subprocess.run(
                [
                    WHISPER_BIN,
                    "-m", WHISPER_MODEL,
                    "-f", str(self.audio_path),
                    "-otxt",
                    "-of", prefix,
                ],
                capture_output=True,
                text=True,
                timeout=WHISPER_TIMEOUT_SECONDS,
            )
            if result.returncode == 0 and transcript_path.exists():
                self.finished.emit(self.recording_id, str(transcript_path))
            else:
                error = result.stderr or f"returncode={result.returncode}"
                self.failed.emit(self.recording_id, error[:200])
        except subprocess.TimeoutExpired:
            self.failed.emit(self.recording_id, "Whisper timed out")
        except Exception as exc:
            self.failed.emit(self.recording_id, str(exc)[:200])


class TranscriptionService:
    def __init__(self, signals: QObject) -> None:
        self._signals = signals
        self._active: dict[QThread, "_TranscriptionWorker"] = {}

    def start(self, recording_id: int, audio_path: Path, filename: str) -> None:
        thread = QThread()
        worker = _TranscriptionWorker(recording_id, audio_path, filename)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(lambda rid, path: self._on_finished(rid, path))
        worker.failed.connect(lambda rid, err: self._on_failed(rid, err))
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=thread: self._active.pop(t, None))
        self._active[thread] = worker  # keeps both alive until thread finishes
        thread.start()

    def _on_finished(self, recording_id: int, transcript_path: str) -> None:
        database.update_transcript_path(recording_id, transcript_path)
        database.update_status(recording_id, STATUS_UNSYNCED)
        self._signals.transcriptionComplete.emit(recording_id)

    def _on_failed(self, recording_id: int, error: str) -> None:
        empty_path = UNSYNCED_DIR / f"__empty_{recording_id}.txt"
        try:
            empty_path.write_text("", encoding="utf-8")
            database.update_transcript_path(recording_id, str(empty_path))
        except Exception:
            pass
        database.update_status(recording_id, STATUS_UNSYNCED)
        self._signals.transcriptionFailed.emit(recording_id, error)
