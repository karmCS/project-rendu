from datetime import datetime

from PyQt5.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import database
from config import COLOR_GREEN, COLOR_RED, COLOR_SYNC, COLOR_TEXT, COLOR_TEXT_MUTED
from services import storage
from services.sync_service import sync_one


def _fmt_last_synced(dt) -> str:
    if dt is None:
        return "Never synced"
    month = dt.strftime("%b")
    hour = dt.hour % 12 or 12
    minute = f"{dt.minute:02d}"
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"Last synced: {dt.day} {month} at {hour}:{minute} {ampm}"


class _SyncWorker(QObject):
    fileResult = pyqtSignal(int, bool, str)
    finished = pyqtSignal()

    @pyqtSlot()
    def run(self) -> None:
        recordings = database.list_unsynced()
        for rec in recordings:
            database.update_status(rec.id, "syncing")
            self.fileResult.emit(rec.id, False, "syncing")
            ok, message = sync_one(rec)
            if ok:
                database.mark_synced(rec.id, datetime.now())
                storage.move_to_synced(rec)
            else:
                database.update_status(rec.id, "sync_failed")
            self.fileResult.emit(rec.id, ok, message)
        self.finished.emit()


class _ResultRow(QWidget):
    def __init__(self, label: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        self._icon = QLabel("·")
        self._icon.setFixedWidth(28)
        self._icon.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 16pt;")
        self._name = QLabel(label)
        self._name.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13pt;")
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignRight)
        self._status.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13pt;")
        layout.addWidget(self._icon)
        layout.addWidget(self._name, stretch=1)
        layout.addWidget(self._status)

    def set_syncing(self) -> None:
        self._icon.setText("⋯")
        self._status.setText("syncing...")

    def set_success(self) -> None:
        self._icon.setText("✓")
        self._icon.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 16pt;")
        self._status.setText("sent")
        self._status.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 13pt;")

    def set_failed(self, message: str) -> None:
        self._icon.setText("✗")
        self._icon.setStyleSheet(f"color: {COLOR_RED}; font-size: 16pt;")
        self._status.setText(message[:40])
        self._status.setStyleSheet(f"color: {COLOR_RED}; font-size: 13pt;")


class SyncScreen(QWidget):
    def __init__(self, signals, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._signals = signals
        self._thread: QThread | None = None
        self._row_map: dict[int, _ResultRow] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(16)

        header = QLabel("Sync to Ally")
        header.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 20pt; font-weight: bold;")
        layout.addWidget(header)

        self._count_label = QLabel("Nothing to sync")
        self._count_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 15pt;")
        layout.addWidget(self._count_label)

        self._sync_btn = QPushButton("SYNC NOW")
        self._sync_btn.setFixedHeight(72)
        self._sync_btn.setMinimumWidth(240)
        self._sync_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLOR_SYNC}; color: white; font-size: 20pt;"
            " font-weight: bold; border-radius: 12px; border: none; }}"
            " QPushButton:disabled { background-color: #1a4080; color: #666666; }"
        )
        self._sync_btn.clicked.connect(self._on_sync_clicked)
        layout.addWidget(self._sync_btn, alignment=Qt.AlignLeft)

        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #333333;")
        layout.addWidget(divider)

        self._last_synced_label = QLabel("Never synced")
        self._last_synced_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13pt;")
        layout.addWidget(self._last_synced_label)

        self._error_banner = QLabel("")
        self._error_banner.setStyleSheet(
            f"color: {COLOR_RED}; font-size: 13pt; background-color: #3a1a1a;"
            " border-radius: 8px; padding: 8px;"
        )
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        self._results_layout = QVBoxLayout(container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(0)
        self._results_layout.addStretch(1)
        results_scroll.setWidget(container)
        layout.addWidget(results_scroll)

        signals.syncFileResult.connect(self._on_file_result)
        signals.syncFinished.connect(self._on_sync_finished)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self, *_args) -> None:
        count = len(database.list_unsynced())
        if count == 0:
            self._count_label.setText("Nothing to sync")
            self._sync_btn.setEnabled(False)
        else:
            noun = "recording" if count == 1 else "recordings"
            self._count_label.setText(f"{count} {noun} ready to sync")
            self._sync_btn.setEnabled(True)
        self._last_synced_label.setText(_fmt_last_synced(database.last_synced_at()))

    def _on_sync_clicked(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self._error_banner.hide()
        self._row_map.clear()
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for rec in database.list_unsynced():
            row = _ResultRow(rec.label or rec.filename)
            self._row_map[rec.id] = row
            self._results_layout.insertWidget(self._results_layout.count() - 1, row)

        self._sync_btn.setEnabled(False)
        self._sync_btn.setText("SYNCING...")

        self._thread = QThread()
        self._worker = _SyncWorker()  # strong ref keeps worker alive until thread finishes
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.fileResult.connect(self._signals.syncFileResult)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._signals.syncFinished)
        self._thread.start()

    def _on_file_result(self, recording_id: int, success: bool, message: str) -> None:
        row = self._row_map.get(recording_id)
        if row is None:
            return
        if message == "syncing":
            row.set_syncing()
        elif success:
            row.set_success()
        else:
            row.set_failed(message)
            if "Could not reach" in message or "Timed out" in message:
                self._error_banner.setText(
                    "Could not reach the Ally. Make sure you're on your home network."
                )
                self._error_banner.show()

    def _on_sync_finished(self, *_args) -> None:
        self._thread = None
        self._worker = None
        self._sync_btn.setText("SYNC NOW")
        self.refresh()
