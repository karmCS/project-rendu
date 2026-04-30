from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import database
from config import (
    COLOR_CARD,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_WAVEFORM,
)
from database import Recording
from screens.touch_keyboard import TouchKeyboard
from services import storage

_LONG_PRESS_MS = 500
_MOVE_THRESHOLD_PX = 10


def _fmt_datetime(dt) -> str:
    if dt is None:
        return ""
    month = dt.strftime("%b")
    hour = dt.hour % 12 or 12
    minute = f"{dt.minute:02d}"
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.day} {month} · {hour}:{minute} {ampm}"


def _fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s"


class StatusBadge(QLabel):
    _MAP = {
        "transcribing": ("#2196f3", "TRANSCRIBING"),
        "unsynced":     ("#4caf50", "READY"),
        "syncing":      ("#2196f3", "SYNCING"),
        "synced":       ("#666666", "SYNCED"),
        "sync_failed":  ("#f44336", "SYNC FAILED"),
    }

    def __init__(self, status: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(26)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        color, text = self._MAP.get(status, ("#666666", status.upper()))
        self.setText(text)
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 10px;"
            " font-size: 11pt; font-weight: bold; padding: 0 10px;"
        )


class RecordingCard(QFrame):
    tapped = pyqtSignal(int)
    renameRequested = pyqtSignal(int)

    def __init__(self, recording: Recording, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.recording_id = recording.id
        self.setFixedHeight(80)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QFrame#card {{ background-color: {COLOR_CARD}; border-radius: 12px; }}"
        )

        self._press_pos = None
        self._long_pressed = False
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.setInterval(_LONG_PRESS_MS)
        self._long_press_timer.timeout.connect(self._on_long_press)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(4)
        self._label_lbl = QLabel(recording.label or recording.filename)
        self._label_lbl.setStyleSheet(
            f"color: {COLOR_TEXT}; font-size: 15pt; font-weight: bold; background: transparent;"
        )
        self._date_lbl = QLabel(_fmt_datetime(recording.recorded_at))
        self._date_lbl.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 12pt; background: transparent;"
        )
        left.addWidget(self._label_lbl)
        left.addWidget(self._date_lbl)

        right = QVBoxLayout()
        right.setSpacing(4)
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._badge = StatusBadge(recording.status)
        self._duration_lbl = QLabel(_fmt_duration(recording.duration_seconds))
        self._duration_lbl.setAlignment(Qt.AlignRight)
        self._duration_lbl.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 12pt; background: transparent;"
        )
        right.addWidget(self._badge)
        right.addWidget(self._duration_lbl)

        self._pencil_btn = QPushButton("✎")
        self._pencil_btn.setFixedSize(48, 48)
        self._pencil_btn.setCursor(Qt.PointingHandCursor)
        self._pencil_btn.setFocusPolicy(Qt.NoFocus)
        self._pencil_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {COLOR_TEXT_MUTED};"
            " font-size: 22pt; border: none; }"
            f"QPushButton:pressed {{ color: {COLOR_WAVEFORM}; }}"
        )
        self._pencil_btn.clicked.connect(
            lambda: self.renameRequested.emit(self.recording_id)
        )

        layout.addLayout(left, stretch=1)
        layout.addLayout(right)
        layout.addWidget(self._pencil_btn)

    def update_recording(self, recording: Recording) -> None:
        self._label_lbl.setText(recording.label or recording.filename)
        self._badge.set_status(recording.status)

    def _on_long_press(self) -> None:
        self._long_pressed = True
        self.renameRequested.emit(self.recording_id)

    def mousePressEvent(self, event) -> None:
        self._long_pressed = False
        self._press_pos = event.pos()
        self._long_press_timer.start()

    def mouseMoveEvent(self, event) -> None:
        if self._press_pos is not None:
            delta = (event.pos() - self._press_pos).manhattanLength()
            if delta > _MOVE_THRESHOLD_PX:
                self._long_press_timer.stop()
                self._press_pos = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        was_pressed = self._press_pos is not None
        self._long_press_timer.stop()
        if was_pressed and not self._long_pressed:
            self.tapped.emit(self.recording_id)
        self._press_pos = None
        self._long_pressed = False


class StorageIndicator(QLabel):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.refresh()

    def refresh(self) -> None:
        gb = storage.disk_free_gb()
        text = f"{gb:.1f} GB free"
        if gb < 1.0:
            color = "#f44336"
        elif gb < 2.0:
            color = "#e6a817"
        else:
            color = "#ffffff"
        self.setText(text)
        self.setStyleSheet(f"color: {color}; font-size: 12pt; background: transparent;")


class RecordingDetailSheet(QDialog):
    def __init__(self, recording: Recording, signals, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._recording = recording
        self._signals = signals
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFixedSize(800, 300)
        self.setStyleSheet("background-color: #222222; border-radius: 16px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        label_row = QHBoxLayout()
        lbl_title = QLabel("Label")
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13pt;")
        self._label_display = QLabel(recording.label or recording.filename)
        self._label_display.setStyleSheet(
            f"color: {COLOR_TEXT}; font-size: 16pt; font-weight: bold;"
        )
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(
            f"background-color: {COLOR_WAVEFORM}; color: white; font-size: 13pt;"
            " border-radius: 8px; min-height: 40px; min-width: 80px; border: none;"
        )
        edit_btn.clicked.connect(self._edit_label)
        label_row.addWidget(lbl_title)
        label_row.addWidget(self._label_display, stretch=1)
        label_row.addWidget(edit_btn)
        layout.addLayout(label_row)

        info = QLabel(
            f"{_fmt_datetime(recording.recorded_at)}   ·   "
            f"{_fmt_duration(recording.duration_seconds)}   ·   "
            f"{recording.status.upper()}"
        )
        info.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13pt;")
        layout.addWidget(info)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "background-color: #444444; color: white; font-size: 16pt; font-weight: bold;"
            " border-radius: 10px; min-height: 60px; border: none;"
        )
        close_btn.clicked.connect(self.accept)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(
            "background-color: #cc3333; color: white; font-size: 16pt; font-weight: bold;"
            " border-radius: 10px; min-height: 60px; border: none;"
        )
        delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(close_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)

    def _edit_label(self) -> None:
        text, ok = TouchKeyboard.get_text(
            self,
            "Edit Label",
            self._recording.label or self._recording.filename,
        )
        if ok and text.strip():
            database.update_label(self._recording.id, text.strip())
            self._label_display.setText(text.strip())
            self._signals.recordingUpdated.emit(self._recording.id)

    def _delete(self) -> None:
        reply = QMessageBox.question(
            self, "Delete Recording",
            "Delete this recording? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            rec = database.delete_recording(self._recording.id)
            if rec:
                storage.delete_recording_files(rec)
            self._signals.recordingDeleted.emit(self._recording.id)
            self.accept()


class RecordingsScreen(QWidget):
    def __init__(self, signals, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._signals = signals
        self._cards: dict[int, RecordingCard] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Recordings")
        title.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 18pt; font-weight: bold;")
        self._storage = StorageIndicator()
        header.addWidget(title)
        header.addWidget(self._storage)
        layout.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(container)
        layout.addWidget(self._scroll)

        self._empty_label = QLabel("No recordings yet.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 14pt;"
        )

        signals.recordingFinished.connect(self.refresh)
        signals.transcriptionComplete.connect(self.refresh)
        signals.transcriptionFailed.connect(lambda rid, _: self.refresh())
        signals.recordingUpdated.connect(self.refresh)
        signals.recordingDeleted.connect(self.refresh)
        signals.syncFinished.connect(self.refresh)
        signals.syncFileResult.connect(self._on_sync_file_result)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
        self._storage.refresh()

    def refresh(self, *_args) -> None:
        recordings = database.list_recordings()
        self._cards.clear()

        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not recordings:
            self._list_layout.insertWidget(0, self._empty_label)
            return

        if self._empty_label.parent():
            self._empty_label.setParent(None)

        for rec in recordings:
            card = RecordingCard(rec)
            card.tapped.connect(self._open_detail)
            card.renameRequested.connect(self._open_rename)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
            self._cards[rec.id] = card

    def _on_sync_file_result(self, recording_id: int, success: bool, message: str) -> None:
        if recording_id in self._cards:
            rec = database.get_recording(recording_id)
            if rec:
                self._cards[recording_id].update_recording(rec)

    def _open_detail(self, recording_id: int) -> None:
        rec = database.get_recording(recording_id)
        if rec is None:
            return
        sheet = RecordingDetailSheet(rec, self._signals, self)
        sheet.exec_()

    def _open_rename(self, recording_id: int) -> None:
        rec = database.get_recording(recording_id)
        if rec is None:
            return
        current = rec.label or rec.filename
        text, ok = TouchKeyboard.get_text(self, "Rename Recording", current)
        if ok and text.strip():
            database.update_label(recording_id, text.strip())
            self._signals.recordingUpdated.emit(recording_id)
