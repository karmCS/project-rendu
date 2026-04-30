from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_WAVEFORM,
    WINDOW_SIZE,
)


_ROW_NUMBERS = "1234567890"
_ROW_TOP = "qwertyuiop"
_ROW_MID = "asdfghjkl"
_ROW_BOT = "zxcvbnm"

_KEY_HEIGHT = 54
_KEY_WIDTH = 70
_WIDE_KEY_WIDTH = 90
_ACTION_KEY_WIDTH = 140


def _key_style() -> str:
    return (
        f"QPushButton {{ background-color: {COLOR_CARD}; color: {COLOR_TEXT};"
        " font-size: 18pt; border-radius: 8px; border: none; }"
        f"QPushButton:pressed {{ background-color: {COLOR_WAVEFORM}; }}"
        f"QPushButton:checked {{ background-color: {COLOR_WAVEFORM}; color: white; }}"
    )


class TouchKeyboard(QDialog):
    def __init__(
        self,
        title: str,
        initial_text: str = "",
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFixedSize(*WINDOW_SIZE)
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        self._shift = False
        self._letter_buttons: list[QPushButton] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 14pt;")
        root.addWidget(title_lbl)

        self._line_edit = QLineEdit(initial_text)
        self._line_edit.setReadOnly(True)
        self._line_edit.setFixedHeight(60)
        self._line_edit.setStyleSheet(
            f"background-color: {COLOR_CARD}; color: {COLOR_TEXT};"
            " font-size: 22pt; border-radius: 8px; padding: 8px 12px;"
            " border: 1px solid #444444;"
        )
        root.addWidget(self._line_edit)

        root.addLayout(self._letter_row(_ROW_NUMBERS, shiftable=False))
        root.addLayout(self._letter_row(_ROW_TOP, shiftable=True))
        root.addLayout(self._letter_row(_ROW_MID, shiftable=True))
        root.addLayout(self._bottom_letter_row())
        root.addLayout(self._action_row())

    def _make_key(self, label: str, width: int = _KEY_WIDTH) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(_KEY_HEIGHT)
        btn.setMinimumWidth(width)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setStyleSheet(_key_style())
        return btn

    def _letter_row(self, letters: str, shiftable: bool) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)
        for ch in letters:
            btn = self._make_key(ch)
            btn.clicked.connect(lambda _c, b=btn: self._on_char(b.text()))
            if shiftable:
                self._letter_buttons.append(btn)
            row.addWidget(btn)
        return row

    def _bottom_letter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)

        shift_btn = self._make_key("Shift", width=_WIDE_KEY_WIDTH)
        shift_btn.setCheckable(True)
        shift_btn.toggled.connect(self._on_shift)
        row.addWidget(shift_btn)

        for ch in _ROW_BOT:
            btn = self._make_key(ch)
            btn.clicked.connect(lambda _c, b=btn: self._on_char(b.text()))
            self._letter_buttons.append(btn)
            row.addWidget(btn)

        bksp = self._make_key("Back", width=_WIDE_KEY_WIDTH)
        bksp.clicked.connect(self._on_backspace)
        row.addWidget(bksp)
        return row

    def _action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(_KEY_HEIGHT)
        cancel.setMinimumWidth(_ACTION_KEY_WIDTH)
        cancel.setFocusPolicy(Qt.NoFocus)
        cancel.setStyleSheet(
            f"QPushButton {{ background-color: #444444; color: {COLOR_TEXT};"
            " font-size: 16pt; font-weight: bold; border-radius: 8px; border: none; }"
        )
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)

        space = self._make_key("Space")
        space.setMinimumWidth(360)
        space.clicked.connect(lambda: self._on_char(" "))
        row.addWidget(space, stretch=1)

        done = QPushButton("Done")
        done.setFixedHeight(_KEY_HEIGHT)
        done.setMinimumWidth(_ACTION_KEY_WIDTH)
        done.setFocusPolicy(Qt.NoFocus)
        done.setStyleSheet(
            f"QPushButton {{ background-color: {COLOR_WAVEFORM}; color: white;"
            " font-size: 16pt; font-weight: bold; border-radius: 8px; border: none; }"
        )
        done.clicked.connect(self.accept)
        row.addWidget(done)
        return row

    def _on_char(self, ch: str) -> None:
        if self._shift and ch.isalpha():
            ch = ch.upper()
        self._line_edit.setText(self._line_edit.text() + ch)

    def _on_backspace(self) -> None:
        self._line_edit.setText(self._line_edit.text()[:-1])

    def _on_shift(self, checked: bool) -> None:
        self._shift = checked
        for btn in self._letter_buttons:
            label = btn.text()
            if label.isalpha():
                btn.setText(label.upper() if checked else label.lower())

    def text(self) -> str:
        return self._line_edit.text()

    @staticmethod
    def get_text(
        parent: QWidget,
        title: str,
        initial_text: str = "",
    ) -> tuple[str, bool]:
        dlg = TouchKeyboard(title, initial_text, parent)
        ok = dlg.exec_() == QDialog.Accepted
        return dlg.text(), ok
