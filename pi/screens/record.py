import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import database
from config import (
    COLOR_BG,
    COLOR_PAUSE,
    COLOR_RECORD,
    COLOR_STOP,
    COLOR_TEXT_MUTED,
    COLOR_WAVEFORM,
    IDLE_TIMEOUT_SECONDS,
    IS_LINUX,
    UNSYNCED_DIR,
    WAVEFORM_UPDATE_MS,
)
from services.audio import make_recorder
from services.transcribe import TranscriptionService

_IDLE = "idle"
_RECORDING = "recording"
_PAUSED = "paused"

_BTN_BASE = (
    "font-size: 20pt; font-weight: bold; border-radius: 48px;"
    " min-height: 96px; min-width: 200px; border: none; color: white;"
)
_PAUSE_BASE = (
    "font-size: 16pt; font-weight: bold; border-radius: 12px;"
    " min-height: 60px; min-width: 160px; border: none; color: white;"
)


class WaveformWidget(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(80)
        self._samples: deque[float] = deque([0.0] * 80, maxlen=80)
        self.setStyleSheet(f"background-color: {COLOR_BG};")

    def set_amplitude(self, value: float) -> None:
        self._samples.append(max(0.0, min(1.0, value)))
        self.update()

    def clear(self) -> None:
        self._samples = deque([0.0] * 80, maxlen=80)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLOR_BG))
        w, h = self.width(), self.height()
        samples = list(self._samples)
        n = len(samples)
        if n == 0:
            return
        bar_w = max(2, w // n)
        gap = max(1, (w - bar_w * n) // max(n - 1, 1))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLOR_WAVEFORM))
        for i, amp in enumerate(samples):
            bar_h = max(3, int(amp * (h - 8)))
            x = i * (bar_w + gap)
            y = (h - bar_h) // 2
            painter.drawRoundedRect(x, y, bar_w, bar_h, 2, 2)


class RecordScreen(QWidget):
    navigateToRecordings = pyqtSignal()

    def __init__(self, signals, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._signals = signals
        self._state = _IDLE
        self._recorder = None
        self._transcription_service = TranscriptionService(signals)
        self._filename = ""

        self._timer = QTimer(self)
        self._timer.setInterval(WAVEFORM_UPDATE_MS)
        self._timer.timeout.connect(self._tick)

        self._build_ui()
        self._apply_state(_IDLE)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        self._status_bar = QLabel("")
        self._status_bar.setAlignment(Qt.AlignCenter)
        self._status_bar.setFixedHeight(28)
        layout.addWidget(self._status_bar)

        self._waveform = WaveformWidget()
        layout.addWidget(self._waveform)

        layout.addStretch(1)

        self._pause_btn = QPushButton("⏸  PAUSE")
        self._pause_btn.setFixedHeight(60)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self._pause_btn, alignment=Qt.AlignCenter)

        self._record_btn = QPushButton("● RECORD")
        self._record_btn.setFixedHeight(96)
        self._record_btn.setMinimumWidth(200)
        self._record_btn.clicked.connect(self._on_record_clicked)
        layout.addWidget(self._record_btn, alignment=Qt.AlignCenter)

        layout.addStretch(1)

    def _apply_state(self, state: str) -> None:
        self._state = state
        if state == _IDLE:
            self._record_btn.setText("● RECORD")
            self._record_btn.setStyleSheet(
                f"background-color: {COLOR_RECORD}; {_BTN_BASE}"
            )
            self._pause_btn.setVisible(False)
            self._status_bar.setText("")
            self._status_bar.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 14pt;")
            self._waveform.clear()

        elif state == _RECORDING:
            self._record_btn.setText("■ STOP")
            self._record_btn.setStyleSheet(
                f"background-color: {COLOR_STOP}; {_BTN_BASE}"
            )
            self._pause_btn.setText("⏸  PAUSE")
            self._pause_btn.setStyleSheet(
                f"background-color: {COLOR_PAUSE}; {_PAUSE_BASE}"
            )
            self._pause_btn.setVisible(True)

        elif state == _PAUSED:
            self._record_btn.setText("■ STOP")
            self._record_btn.setStyleSheet(
                f"background-color: {COLOR_STOP}; {_BTN_BASE}"
            )
            self._pause_btn.setText("▶  RESUME")
            self._pause_btn.setStyleSheet(
                f"background-color: {COLOR_PAUSE}; {_PAUSE_BASE}"
            )
            self._pause_btn.setVisible(True)
            self._waveform.clear()

    def _tick(self) -> None:
        if self._recorder is None:
            return
        elapsed = self._recorder.elapsed_seconds
        if self._state == _RECORDING:
            self._status_bar.setText(f"● RECORDING   {self._format_elapsed(elapsed)}")
            self._status_bar.setStyleSheet(
                "color: #cc3333; font-size: 14pt; font-weight: bold;"
            )
            self._waveform.set_amplitude(self._recorder.latest_rms)
        elif self._state == _PAUSED:
            self._status_bar.setText(f"⏸ PAUSED   {self._format_elapsed(elapsed)}")
            self._status_bar.setStyleSheet(
                f"color: {COLOR_PAUSE}; font-size: 14pt; font-weight: bold;"
            )

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"

    def _on_record_clicked(self) -> None:
        if self._state == _IDLE:
            self._start_recording()
        else:
            self._stop_recording()

    def _on_pause_clicked(self) -> None:
        if self._state == _RECORDING:
            self._recorder.pause()
            self._apply_state(_PAUSED)
        elif self._state == _PAUSED:
            self._recorder.resume()
            self._apply_state(_RECORDING)

    def _start_recording(self) -> None:
        self._filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        audio_path = UNSYNCED_DIR / f"{self._filename}.wav"
        try:
            self._recorder = make_recorder(audio_path)
            self._recorder.start()
        except Exception as exc:
            self._recorder = None
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass
            QMessageBox.warning(
                self,
                "Microphone unavailable",
                "Could not start recording. Check that the microphone is "
                f"plugged in, then try again.\n\n{exc}",
            )
            self._apply_state(_IDLE)
            return
        if IS_LINUX:
            subprocess.run(["xset", "s", "off"], capture_output=True)
            subprocess.run(["xset", "-dpms"], capture_output=True)
        self._timer.start()
        self._apply_state(_RECORDING)

    def _stop_recording(self) -> None:
        if self._recorder is None:
            return
        self._timer.stop()
        duration = self._recorder.stop()
        if IS_LINUX:
            subprocess.run(["xset", "s", str(IDLE_TIMEOUT_SECONDS)], capture_output=True)
            subprocess.run(["xset", "+dpms"], capture_output=True)
        audio_path = str(UNSYNCED_DIR / f"{self._filename}.wav")
        rec_id = database.insert_recording(
            filename=self._filename,
            label=self._filename,
            audio_path=audio_path,
            duration_seconds=duration,
        )
        self._recorder = None
        self._apply_state(_IDLE)
        self._signals.recordingFinished.emit(rec_id)
        self._transcription_service.start(rec_id, Path(audio_path), self._filename)
        self.navigateToRecordings.emit()

    def cleanup(self) -> None:
        if self._recorder and (self._recorder.is_recording or self._recorder.is_paused):
            self._timer.stop()
            self._recorder.stop()
