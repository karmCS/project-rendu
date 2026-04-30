import subprocess
import sys

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import database
from config import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_GREEN,
    COLOR_PAUSE,
    COLOR_RED,
    COLOR_STOP,
    COLOR_SYNC,
    COLOR_TAB_ACTIVE,
    COLOR_TAB_BG,
    COLOR_TAB_INACTIVE,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_WAVEFORM,
    IDLE_TIMEOUT_SECONDS,
    IS_LINUX,
    WINDOW_SIZE,
    TAB_BAR_HEIGHT,
)


class AppSignals(QObject):
    recordingFinished = pyqtSignal(int)
    transcriptionComplete = pyqtSignal(int)
    transcriptionFailed = pyqtSignal(int, str)
    recordingDeleted = pyqtSignal(int)
    recordingUpdated = pyqtSignal(int)
    syncFileResult = pyqtSignal(int, bool, str)
    syncFinished = pyqtSignal()


def _build_stylesheet() -> str:
    return f"""
        QWidget {{
            background-color: {COLOR_BG};
            color: {COLOR_TEXT};
            font-size: 16pt;
        }}
        QScrollArea {{ border: none; }}
        QScrollBar:vertical {{
            background: {COLOR_BG};
            width: 6px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: #444444;
            border-radius: 3px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QDialog {{ background-color: #222222; }}
        QInputDialog {{ background-color: {COLOR_CARD}; color: {COLOR_TEXT}; }}
        QMessageBox {{ background-color: {COLOR_CARD}; color: {COLOR_TEXT}; }}
        QMessageBox QPushButton {{
            background-color: {COLOR_STOP};
            color: {COLOR_TEXT};
            border-radius: 8px;
            padding: 8px 20px;
            font-size: 14pt;
            border: none;
        }}
        QInputDialog QLineEdit {{
            background-color: {COLOR_BG};
            color: {COLOR_TEXT};
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 6px;
        }}
    """


class TabBar(QWidget):
    tabSelected = pyqtSignal(int)

    _LABELS = ["Record", "Recordings", "Sync"]

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TAB_BAR_HEIGHT)
        self._buttons: list[QPushButton] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for i, label in enumerate(self._LABELS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda _checked, idx=i: self._select(idx))
            self._buttons.append(btn)
            layout.addWidget(btn)
        self._apply_styles(0)

    def _select(self, index: int) -> None:
        self._apply_styles(index)
        self.tabSelected.emit(index)

    def _apply_styles(self, active_index: int) -> None:
        for i, btn in enumerate(self._buttons):
            active = i == active_index
            btn.setChecked(active)
            color = COLOR_TAB_ACTIVE if active else COLOR_TAB_INACTIVE
            border = (
                f"border-top: 3px solid {COLOR_WAVEFORM};"
                if active
                else "border-top: 3px solid transparent;"
            )
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {color};
                    background-color: {COLOR_TAB_BG};
                    border: none;
                    {border}
                    font-size: 14pt;
                    padding: 0;
                }}
            """)

    def set_active(self, index: int) -> None:
        self._select(index)


class MainWindow(QMainWindow):
    def __init__(self, signals: AppSignals) -> None:
        super().__init__()
        self._signals = signals
        self.setWindowTitle("Rendu")
        self.setFixedSize(*WINDOW_SIZE)
        if IS_LINUX:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._tab_bar = TabBar()
        root.addWidget(self._tab_bar)

        from screens.record import RecordScreen
        from screens.recordings import RecordingsScreen
        from screens.sync import SyncScreen

        self._record_screen = RecordScreen(signals)
        self._recordings_screen = RecordingsScreen(signals)
        self._sync_screen = SyncScreen(signals)

        self._stack.addWidget(self._record_screen)
        self._stack.addWidget(self._recordings_screen)
        self._stack.addWidget(self._sync_screen)

        self._tab_bar.tabSelected.connect(self._stack.setCurrentIndex)
        self._record_screen.navigateToRecordings.connect(
            lambda: self._tab_bar.set_active(1)
        )

    def closeEvent(self, event) -> None:
        self._record_screen.cleanup()
        super().closeEvent(event)


def main() -> None:
    database.init_db()

    if IS_LINUX:
        subprocess.run(["xset", "s", str(IDLE_TIMEOUT_SECONDS)], capture_output=True)
        subprocess.run(["xset", "+dpms"], capture_output=True)

    app = QApplication(sys.argv)
    app.setStyleSheet(_build_stylesheet())

    signals = AppSignals()
    window = MainWindow(signals)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
