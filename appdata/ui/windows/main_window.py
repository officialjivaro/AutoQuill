# appdata/ui/windows/main_window.py
"""
Main application window UI.

This is the long-term home for AutoQuillApp.
The main window keeps live typing information and opens the dedicated
typing settings dialog when needed.
"""

import threading
import time
from typing import Optional

from pynput import keyboard
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from appdata.core.configs.constants import APP_NAME, DEFAULT_WPM, FUNCTION_KEYS
from appdata.core.controllers.main_window_controller import MainWindowLogic
from appdata.core.templating.runtime_vars import get_supported_tokens
from appdata.core.version.model import VERSION
from appdata.ui.dialogs.typing_settings_dialog import TypingSettingsDialog
from appdata.ui.themes.app_theme import apply_app_theme, set_widget_role, set_widget_state


class AutoQuillApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setWindowIcon(QIcon("appdata/resources/images/icon.ico"))
        self.resize(500, 600)

        self.function_key = FUNCTION_KEYS[0]
        self.function_key_lower = self.function_key.lower()

        self.default_wpm = DEFAULT_WPM
        self.wpm = self.default_wpm

        self.default_sticky_typing = False

        self.default_stop_after_enabled = False
        self.default_stop_after_seconds = 60

        self.default_simulate_pauses_enabled = False
        self.default_pause_every_min_chars = 120
        self.default_pause_every_max_chars = 250
        self.default_pause_min_seconds = 0.6
        self.default_pause_max_seconds = 1.8

        self.simulate_human_errors = False
        self.typing_active_evt = threading.Event()
        self.typing_paused_evt = threading.Event()
        self.typing_thread = None

        self.default_min_interval = 15
        self.default_max_interval = 40
        self.default_min_errors = 1
        self.default_max_errors = 4

        self.default_breaks_enabled = False
        self.default_breaks_word_min = 18
        self.default_breaks_word_max = 42
        self.default_breaks_sec_min = 2.0
        self.default_breaks_sec_max = 5.0

        self.run_lock = threading.Lock()
        self.run_status = "Idle"  # Idle | Typing | Paused
        self.run_typed_chars = 0
        self.run_total_chars = 0
        self.run_started_at = 0.0
        self.run_paused_total = 0.0
        self.run_paused_since: Optional[float] = None
        self.run_ended_at: Optional[float] = None

        self.logic = MainWindowLogic(self)
        apply_app_theme(self)
        self.init_ui()

        # The settings dialog owns the moved auto-typer controls and profile UI.
        self.settings_dialog = TypingSettingsDialog(self)

        self.create_menu()
        self.start_keyboard_listener()
        self.refresh_save_list()
        self._refresh_header_context()
        self._start_progress_timer()

    def create_menu(self):
        mb = QMenuBar(self)
        self.setMenuBar(mb)

        fm = mb.addMenu("File")
        install = QAction("Install", self)
        install.triggered.connect(self.logic.install_action)
        fm.addAction(install)

        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.logic.exit_app)
        fm.addAction(exit_act)

        hm = mb.addMenu("Help")

        about_instanciar = QAction("About Instanciar", self)
        about_instanciar.triggered.connect(self.logic.open_commands)
        hm.addAction(about_instanciar)

        about_jivaro = QAction("About Jivaro", self)
        about_jivaro.triggered.connect(self.logic.open_about_jivaro)
        hm.addAction(about_jivaro)

        join_discord = QAction("Join Discord", self)
        join_discord.triggered.connect(self.logic.open_discord)
        hm.addAction(join_discord)

        get_proxies = QAction("Get Proxies", self)
        get_proxies.triggered.connect(self.logic.open_proxies)
        hm.addAction(get_proxies)

    def init_ui(self):
        cw = QWidget()
        cw.setObjectName("MainCentralWidget")
        self.setCentralWidget(cw)

        layout = QVBoxLayout(cw)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._build_typing_group(layout)
        self._build_text_group(layout)

    def _build_typing_group(self, parent_layout: QVBoxLayout) -> None:
        session_card = QFrame()
        session_card.setObjectName("SessionCard")

        card_layout = QVBoxLayout(session_card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(10)

        accent_strip = QFrame()
        accent_strip.setObjectName("AccentStrip")
        accent_strip.setFixedHeight(6)
        card_layout.addWidget(accent_strip)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        session_title = QLabel("Live session")
        set_widget_role(session_title, "cardTitle")
        title_row.addWidget(session_title)

        title_row.addStretch(1)

        self.status_val = QLabel("Idle")
        self.status_val.setObjectName("StatusPill")
        self.status_val.setAlignment(Qt.AlignCenter)
        self.status_val.setMinimumWidth(92)
        self._update_status_style("Idle")
        title_row.addWidget(self.status_val)

        card_layout.addLayout(title_row)

        self.progress_val = QLabel("Typed 0/0 chars • ETA --:--")
        set_widget_role(self.progress_val, "progressText")
        card_layout.addWidget(self.progress_val)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(14)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)

        self.hotkey_chip = self._make_meta_chip("Hotkey --")
        self.wpm_chip = self._make_meta_chip("-- WPM")
        self.sticky_chip = self._make_meta_chip("Sticky Off")
        self.profile_chip = self._make_meta_chip("Profile Unsaved")

        chips_row.addWidget(self.hotkey_chip)
        chips_row.addWidget(self.wpm_chip)
        chips_row.addWidget(self.sticky_chip)
        chips_row.addWidget(self.profile_chip)
        chips_row.addStretch(1)
        card_layout.addLayout(chips_row)

        self.target_status_val = QLabel("Sticky target: Off")
        self.target_status_val.setObjectName("TargetStatus")
        self.target_status_val.setWordWrap(True)
        self._apply_target_status_style("muted")
        card_layout.addWidget(self.target_status_val)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(self.settings_btn, "secondary")
        self.settings_btn.setToolTip(
            "Open typing settings such as hotkey, WPM, looping, simulation options, and profiles."
        )
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(self.reset_btn, "danger")
        self.reset_btn.setToolTip("Stop typing (if active) and reset progress back to 0.")
        self.reset_btn.clicked.connect(self.on_reset_clicked)

        actions_row.addWidget(self.settings_btn)
        actions_row.addWidget(self.reset_btn)
        actions_row.addStretch(1)
        card_layout.addLayout(actions_row)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(8)

        profile_lab = QLabel("Quick profile:")
        set_widget_role(profile_lab, "sectionHint")

        self.profile_quick_combo = QComboBox()
        self.profile_quick_combo.setMinimumWidth(180)
        self.profile_quick_combo.setToolTip("Choose a saved profile to load from the main window.")

        self.profile_quick_load_btn = QPushButton("Load")
        self.profile_quick_load_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(self.profile_quick_load_btn, "secondary")
        self.profile_quick_load_btn.setFixedWidth(84)
        self.profile_quick_load_btn.setToolTip("Load the selected saved profile.")
        self.profile_quick_load_btn.clicked.connect(self.on_quick_profile_load_clicked)

        profile_row.addWidget(profile_lab)
        profile_row.addWidget(self.profile_quick_combo, 1)
        profile_row.addWidget(self.profile_quick_load_btn)
        card_layout.addLayout(profile_row)

        parent_layout.addWidget(session_card)

    def _build_text_group(self, parent_layout: QVBoxLayout) -> None:
        text_box = QGroupBox("Text to type")
        text_layout = QVBoxLayout(text_box)
        text_layout.setContentsMargins(12, 10, 12, 10)
        text_layout.setSpacing(8)

        token_row = QHBoxLayout()
        token_row.setSpacing(6)

        token_label = QLabel("Quick tokens:")
        token_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        token_label.setToolTip("These placeholders are replaced right before typing starts.")
        set_widget_role(token_label, "sectionHint")
        token_row.addWidget(token_label)

        for token_info in get_supported_tokens():
            btn = QPushButton(token_info["token"])
            btn.setCursor(Qt.PointingHandCursor)
            set_widget_role(btn, "token")
            btn.setToolTip(token_info["description"])
            btn.clicked.connect(
                lambda _checked=False, token=token_info["token"]: self.insert_token_at_cursor(token)
            )
            token_row.addWidget(btn)

        token_row.addStretch(1)
        text_layout.addLayout(token_row)

        helper_hint = QLabel("Tokens are expanded when typing starts.")
        set_widget_role(helper_hint, "sectionHint")
        helper_hint.setToolTip(
            "Example: {DATE}, {TIME}, and {CLIPBOARD} are turned into real values right before typing."
        )
        text_layout.addWidget(helper_hint)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter text to type (plain text only)...")
        text_layout.addWidget(self.text_edit)

        parent_layout.addWidget(text_box, 1)

        support_row = QHBoxLayout()
        support_row.setSpacing(0)
        support_row.addStretch(1)

        support_card = QFrame()
        support_card.setObjectName("SupportCard")

        support_layout = QHBoxLayout(support_card)
        support_layout.setContentsMargins(10, 8, 10, 8)
        support_layout.setSpacing(10)

        support_label = QLabel("Enjoying AutoQuill?")
        set_widget_role(support_label, "supportHint")

        self.donate_btn = QPushButton("Support AutoQuill")
        self.donate_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(self.donate_btn, "support")
        self.donate_btn.setToolTip("Support AutoQuill and Jivaro with a donation.")
        self.donate_btn.clicked.connect(self.logic.open_donate)

        support_layout.addWidget(support_label)
        support_layout.addWidget(self.donate_btn)

        support_row.addWidget(support_card)
        parent_layout.addLayout(support_row)

    def _make_meta_chip(self, text: str) -> QLabel:
        label = QLabel(text)
        set_widget_role(label, "metaChip")
        return label

    @staticmethod
    def _truncate_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return f"{text[: max(0, limit - 1)].rstrip()}…"

    def insert_token_at_cursor(self, token_text: str) -> None:
        """
        Insert a supported runtime token exactly where the cursor is in the main text box.
        """
        cursor = self.text_edit.textCursor()
        cursor.insertText(token_text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()

    def _start_progress_timer(self) -> None:
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(150)
        self._progress_timer.timeout.connect(self._refresh_progress_ui)
        self._progress_timer.start()

    def _refresh_progress_ui(self) -> None:
        with self.run_lock:
            status = self.run_status
            typed = int(self.run_typed_chars)
            total = int(self.run_total_chars)
            started_at = float(self.run_started_at)
            paused_total = float(self.run_paused_total)
            paused_since = self.run_paused_since
            ended_at = self.run_ended_at

        if total < 0:
            total = 0
        if typed < 0:
            typed = 0
        if total > 0 and typed > total:
            typed = total

        self.status_val.setText(status)
        self._update_status_style(status)
        self._refresh_target_status()

        if total <= 0:
            self.progress_val.setText("Typed 0/0 chars • ETA --:--")
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            return

        if started_at <= 0.0:
            active_elapsed = 0.0
        else:
            if status == "Paused" and paused_since is not None:
                now = float(paused_since)
            elif status == "Idle" and ended_at is not None:
                now = float(ended_at)
            else:
                now = time.monotonic()

            active_elapsed = now - started_at - paused_total

        if active_elapsed < 0.0:
            active_elapsed = 0.0

        eta_txt = "--:--"
        if typed >= 10 and active_elapsed > 0.0 and typed < total:
            cps = typed / active_elapsed
            if cps > 0.0:
                eta_s = int(round((total - typed) / cps))
                eta_txt = self._format_mm_ss(eta_s)
        elif typed >= total and total > 0:
            eta_txt = "00:00"

        self.progress_val.setText(f"Typed {typed}/{total} chars • ETA {eta_txt}")
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(typed)

    def _refresh_setup_chips(self) -> None:
        """
        Refresh the mostly-static setup chips.

        This intentionally runs on demand instead of every 150 ms timer tick.
        """
        defaults = {
            "function_key": "--",
            "wpm": "--",
            "sticky_typing": False,
            "profile_name": "Unsaved",
        }

        try:
            summary = self.settings_dialog.get_header_summary()
        except Exception:
            summary = defaults

        function_key = str(summary.get("function_key", defaults["function_key"]))
        wpm = str(summary.get("wpm", defaults["wpm"]))
        sticky_enabled = bool(summary.get("sticky_typing", defaults["sticky_typing"]))
        profile_name = str(summary.get("profile_name", defaults["profile_name"])).strip() or "Unsaved"

        self.hotkey_chip.setText(f"Hotkey {function_key}")
        self.wpm_chip.setText(f"{wpm} WPM")
        self.sticky_chip.setText(f"Sticky {'On' if sticky_enabled else 'Off'}")
        self.profile_chip.setText(self._truncate_text(f"Profile {profile_name}", 24))

    def _refresh_target_status(self) -> None:
        """
        Refresh only the live sticky-target state.

        This stays on the fast timer because the captured target can change during a run.
        """
        try:
            target_status = self.logic.get_target_status()
            self.target_status_val.setText(target_status["text"])
            self._apply_target_status_style(target_status["level"])
        except Exception:
            self.target_status_val.setText("Sticky target: Status unavailable")
            self._apply_target_status_style("warn")

    def _refresh_header_context(self) -> None:
        """
        Refresh header content without pushing all of it through the fast timer.
        """
        self._refresh_setup_chips()
        self._refresh_target_status()

    def _refresh_profile_quick_switch(self) -> None:
        """
        Refresh the small profile picker shown in the main window header.
        """
        try:
            state = self.settings_dialog.get_profile_switch_state()
            names = state["names"]
            current_name = state["current_name"]
        except Exception:
            names = []
            current_name = ""

        self.profile_quick_combo.blockSignals(True)
        self.profile_quick_combo.clear()
        self.profile_quick_combo.addItems(names)

        if current_name and current_name in names:
            self.profile_quick_combo.setCurrentText(current_name)
        elif names:
            self.profile_quick_combo.setCurrentIndex(0)

        self.profile_quick_combo.blockSignals(False)

        has_profiles = bool(names)
        self.profile_quick_combo.setEnabled(has_profiles)
        self.profile_quick_load_btn.setEnabled(has_profiles)

    def _update_status_style(self, status: str) -> None:
        status_states = {
            "Idle": "idle",
            "Typing": "typing",
            "Paused": "paused",
        }
        set_widget_state(self.status_val, status_states.get(status, "idle"))

    def _apply_target_status_style(self, level: str) -> None:
        target_states = {
            "ok": "ok",
            "warn": "warn",
            "muted": "muted",
        }
        set_widget_state(self.target_status_val, target_states.get(level, "muted"))

    @staticmethod
    def _format_mm_ss(seconds: int) -> str:
        if seconds < 0:
            seconds = 0
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def open_settings_dialog(self) -> None:
        # Refresh profile names before opening, then refresh again after closing
        # in case the user saved or loaded a profile while the dialog was open.
        self.refresh_save_list()
        self.settings_dialog.exec()
        self.refresh_save_list()

    def on_reset_clicked(self) -> None:
        """Stop any current typing run and reset progress back to 0."""
        self.logic.reset_typing()

    def on_quick_profile_load_clicked(self) -> None:
        name = self.profile_quick_combo.currentText().strip()
        if not name:
            return

        if self.settings_dialog.load_profile_by_name(name):
            self.refresh_save_list()
        else:
            QMessageBox.warning(self, "Load failed", "Selected configuration is invalid or missing.")

    def refresh_save_list(self):
        self.settings_dialog.refresh_save_list()
        self._refresh_profile_quick_switch()
        self._refresh_header_context()

    # These pass-through methods keep the main window focused on live typing UI,
    # while the dialog owns settings behavior and validation.
    def on_save_clicked(self):
        self.settings_dialog.on_save_clicked()

    def on_load_clicked(self):
        self.settings_dialog.on_load_clicked()

    def on_fkey_changed(self, t):
        self.settings_dialog.on_fkey_changed(t)

    def on_wpm_changed(self, t: str):
        self.settings_dialog.on_wpm_changed(t)

    def on_wpm_editing_finished(self):
        self.settings_dialog.on_wpm_editing_finished()

    def on_toggled_breaks(self, checked: bool):
        self.settings_dialog.on_toggled_breaks(checked)

    def on_toggled_loop(self, checked: bool):
        self.settings_dialog.on_toggled_loop(checked)

    def on_toggled_stop_after(self, checked: bool):
        self.settings_dialog.on_toggled_stop_after(checked)

    def on_stop_after_editing_finished(self):
        self.settings_dialog.on_stop_after_editing_finished()

    def on_toggled_simulate_errors(self, enabled: bool):
        self.settings_dialog.on_toggled_simulate_errors(enabled)

    def on_toggled_simulate_pauses(self, enabled: bool):
        self.settings_dialog.on_toggled_simulate_pauses(enabled)

    def start_keyboard_listener(self):
        self.listener = keyboard.Listener(on_release=self.on_key_release)
        self.listener.start()

    def on_key_release(self, k):
        self.logic.handle_key_press(k)

    def start_typing(self):
        self.logic.start_typing()

    def stop_typing(self):
        self.logic.stop_typing()

    def invoke_typing_logic(self):
        self.logic.invoke_typing_logic()