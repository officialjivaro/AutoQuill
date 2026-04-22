# appdata/ui/themes/app_theme.py
"""
Shared AutoQuill UI theme helpers.

This stays inside appdata/ui/themes/ on purpose.
The role/state helpers let the main window and settings dialog share one
visual system without scattering styles across many widgets.
"""

from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget


APP_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0f141b;
    color: #e8edf3;
}

QWidget#MainCentralWidget,
QWidget#SettingsDialogRoot {
    background-color: #0f141b;
}

QMenuBar {
    background-color: #141b24;
    color: #eef3f8;
    border-bottom: 1px solid #263140;
    padding: 4px 6px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 8px;
}

QMenuBar::item:selected {
    background-color: #1e2a38;
}

QMenu {
    background-color: #141b24;
    color: #eef3f8;
    border: 1px solid #263140;
    padding: 6px;
}

QMenu::item {
    padding: 7px 16px;
    border-radius: 8px;
}

QMenu::item:selected {
    background-color: #223245;
}

QGroupBox {
    background-color: #151c24;
    border: 1px solid #273445;
    border-radius: 16px;
    margin-top: 14px;
    padding-top: 10px;
    color: #e8edf3;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #f4f8fb;
    font-weight: 600;
}

QGroupBox#WarningsBox {
    background-color: #18150f;
    border-color: #5a4620;
}

QGroupBox#WarningsBox::title {
    color: #f0c674;
}

QLineEdit,
QComboBox,
QPlainTextEdit {
    background-color: #0f1720;
    color: #edf2f7;
    border: 1px solid #2b3b4e;
    border-radius: 10px;
    padding: 7px 10px;
    selection-background-color: #335b8a;
}

QLineEdit:hover,
QComboBox:hover,
QPlainTextEdit:hover {
    border-color: #3f5872;
}

QLineEdit:focus,
QComboBox:focus,
QPlainTextEdit:focus {
    border: 1px solid #4f8ccf;
}

QLineEdit:disabled,
QComboBox:disabled,
QPlainTextEdit:disabled {
    background-color: #131b24;
    color: #7f8b98;
    border-color: #1f2a36;
}

QComboBox {
    padding-right: 24px;
}

QComboBox::drop-down {
    width: 24px;
    border: none;
    border-left: 1px solid #2b3b4e;
    background-color: #16202b;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}

QComboBox QAbstractItemView {
    background-color: #141b24;
    color: #edf2f7;
    border: 1px solid #263140;
    selection-background-color: #223245;
}

QPlainTextEdit {
    border-radius: 14px;
    padding: 10px 12px;
}

QProgressBar {
    background-color: #0d131a;
    border: 1px solid #263140;
    border-radius: 7px;
}

QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4c8ff5,
        stop: 1 #7ab3ff
    );
}

/* Base button styling: this is where the “pop” and hover/click feedback lives. */
QPushButton {
    min-height: 34px;
    background-color: #1b2836;
    color: #edf3f9;
    border: 1px solid #3a5066;
    border-radius: 11px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #24374a;
    border-color: #6ea8e3;
}

QPushButton:pressed {
    background-color: #16212d;
    border-color: #4f7eab;
}

QPushButton:focus {
    border-color: #88c2ff;
}

QPushButton:disabled {
    background-color: #151c24;
    color: #748190;
    border-color: #263140;
}

QPushButton[role="secondary"] {
    background-color: #18222d;
    border-color: #334557;
}

QPushButton[role="secondary"]:hover {
    background-color: #213041;
    border-color: #6799ce;
}

QPushButton[role="secondary"]:pressed {
    background-color: #16212d;
    border-color: #4f7da9;
}

QPushButton[role="secondary"]:focus {
    border-color: #88c2ff;
}

QPushButton[role="primary"] {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2f6fed,
        stop: 1 #4b97ff
    );
    border-color: #76b2ff;
    color: #f8fbff;
}

QPushButton[role="primary"]:hover {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #3a7cf4,
        stop: 1 #5aa4ff
    );
    border-color: #a8d0ff;
}

QPushButton[role="primary"]:pressed {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #285fd0,
        stop: 1 #437fd7
    );
    border-color: #6fa4ea;
}

QPushButton[role="primary"]:focus {
    border-color: #c4e0ff;
}

QPushButton[role="danger"] {
    background-color: #2a1b20;
    border-color: #8b4b58;
    color: #ffdbe0;
}

QPushButton[role="danger"]:hover {
    background-color: #362127;
    border-color: #c46b7c;
}

QPushButton[role="danger"]:pressed {
    background-color: #24171b;
    border-color: #9f5967;
}

QPushButton[role="danger"]:focus {
    border-color: #ffc2cb;
}

QPushButton[role="token"] {
    min-height: 28px;
    padding: 6px 12px;
    border-radius: 14px;
    background-color: #14202b;
    border-color: #35506b;
    color: #e7f0fa;
}

QPushButton[role="token"]:hover {
    background-color: #1a2b3b;
    border-color: #6ea8e3;
}

QPushButton[role="token"]:pressed {
    background-color: #13212d;
    border-color: #4f7eab;
}

QPushButton[role="token"]:focus {
    border-color: #88c2ff;
}

QPushButton[role="support"] {
    min-height: 36px;
    padding: 8px 18px;
    border-radius: 12px;
    color: #fff8eb;
    font-weight: 700;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #9155ff,
        stop: 1 #e86f6f
    );
    border: 1px solid #ffc4c4;
}

QPushButton[role="support"]:hover {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #a168ff,
        stop: 1 #f18383
    );
    border-color: #ffe0b3;
}

QPushButton[role="support"]:pressed {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #7f48df,
        stop: 1 #cf6161
    );
    border-color: #ffcf9f;
}

QPushButton[role="support"]:focus {
    border-color: #ffe7c7;
}

QPushButton[role="secondary"]:disabled,
QPushButton[role="primary"]:disabled,
QPushButton[role="danger"]:disabled,
QPushButton[role="token"]:disabled,
QPushButton[role="support"]:disabled {
    background: #151c24;
    color: #748190;
    border-color: #263140;
}

QLabel[role="cardTitle"] {
    color: #f4f8fb;
    font-size: 14px;
    font-weight: 700;
}

QLabel[role="progressText"] {
    color: #c4cfda;
    font-size: 12px;
}

QLabel[role="metaChip"] {
    background-color: #121a24;
    border: 1px solid #2a3748;
    border-radius: 14px;
    padding: 4px 10px;
    color: #dde6ef;
    font-weight: 600;
}

QLabel[role="sectionHint"] {
    color: #9aa8b8;
}

QLabel[role="supportHint"] {
    color: #c8d2dc;
    font-weight: 600;
}

QLabel#StatusPill {
    min-width: 88px;
    padding: 6px 14px;
    border-radius: 14px;
    font-size: 13px;
    font-weight: 700;
}

QLabel#StatusPill[state="idle"] {
    background-color: #223141;
    border: 1px solid #3c5269;
    color: #dbe3ea;
}

QLabel#StatusPill[state="typing"] {
    background-color: #163321;
    border: 1px solid #2d8a50;
    color: #bbefc6;
}

QLabel#StatusPill[state="paused"] {
    background-color: #3a3115;
    border: 1px solid #b48b29;
    color: #f6d484;
}

QLabel#TargetStatus {
    padding: 7px 10px;
    border-radius: 12px;
    font-weight: 600;
}

QLabel#TargetStatus[state="muted"] {
    background-color: #121a24;
    border: 1px solid #2a3748;
    color: #b9c5d0;
}

QLabel#TargetStatus[state="ok"] {
    background-color: #153222;
    border: 1px solid #2d8a50;
    color: #bbefc6;
}

QLabel#TargetStatus[state="warn"] {
    background-color: #382d12;
    border: 1px solid #b48b29;
    color: #f5d385;
}

QLabel#WarningsValue[state="normal"] {
    color: #9aa3ad;
}

QLabel#WarningsValue[state="warning"] {
    color: #f0c674;
}

QCheckBox,
QGroupBox {
    spacing: 8px;
}

QCheckBox::indicator,
QGroupBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #3a4c60;
    background-color: #101720;
}

QCheckBox::indicator:hover,
QGroupBox::indicator:hover {
    border-color: #5a7ca3;
}

QCheckBox::indicator:checked,
QGroupBox::indicator:checked {
    border-color: #6da8ff;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #2f6fed,
        stop: 1 #66b1ff
    );
}

QFrame#SessionCard,
QFrame#SupportCard {
    background-color: #151c24;
    border: 1px solid #273445;
    border-radius: 18px;
}

QFrame#SupportCard {
    border-radius: 14px;
}

QFrame#AccentStrip {
    min-height: 6px;
    max-height: 6px;
    border: none;
    border-radius: 8px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4c8ff5,
        stop: 0.5 #8a6cff,
        stop: 1 #ff7b8b
    );
}
"""


def _repolish(widget: Optional[QWidget]) -> None:
    """
    Re-apply styling after a dynamic property change.
    """
    if widget is None:
        return

    style = widget.style()
    if style is None:
        return

    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def apply_app_theme(widget: Optional[QWidget] = None) -> None:
    """
    Apply the shared stylesheet once at the application level.
    """
    app = QApplication.instance()
    if app is None:
        return

    if app.styleSheet() != APP_STYLESHEET:
        app.setStyleSheet(APP_STYLESHEET)

    _repolish(widget)


def set_widget_role(widget: Optional[QWidget], role: str) -> None:
    """
    Set a stable visual role such as primary, secondary, danger, token, or support.
    """
    if widget is None:
        return
    if widget.property("role") == role:
        return

    widget.setProperty("role", role)
    _repolish(widget)


def set_widget_state(widget: Optional[QWidget], state: str) -> None:
    """
    Set a dynamic visual state such as typing, paused, warning, or muted.
    """
    if widget is None:
        return
    if widget.property("state") == state:
        return

    widget.setProperty("state", state)
    _repolish(widget)