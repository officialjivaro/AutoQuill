# File: appdata/ui/main.py
import threading
import time
from typing import Optional

from pynput import keyboard
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QDoubleValidator, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from appdata.core.ads.adsense import create_adsense_view, load_adsense_content
from appdata.core.constants import APP_NAME, DEFAULT_WPM, FUNCTION_KEYS, WPM_MAX, WPM_MIN
from appdata.core.main_window import MainWindowLogic
from appdata.core.version.model import VERSION


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
        self.init_ui()
        self.create_menu()
        self.start_keyboard_listener()
        self.refresh_save_list()
        self._start_progress_timer()

    def create_menu(self):
        mb = QMenuBar(self)
        self.setMenuBar(mb)
        mb.setStyleSheet(
            "QMenuBar{background:#323232;color:#fff;}"
            "QMenu{background:#323232;color:#fff;}"
            "QMenuBar::item:selected,QMenu::item:selected{background:#454545;}"
        )
        fm = mb.addMenu("File")
        install = QAction("Install", self)
        install.triggered.connect(self.logic.install_action)
        fm.addAction(install)
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.logic.exit_app)
        fm.addAction(exit_act)

        hm = mb.addMenu("Help")
        cmd = QAction("Commands", self)
        cmd.triggered.connect(self.logic.open_commands)
        hm.addAction(cmd)
        prxs = QAction("Proxies", self)
        prxs.triggered.connect(self.logic.open_proxies)
        hm.addAction(prxs)
        about = QAction("About Jivaro", self)
        about.triggered.connect(self.logic.open_about_jivaro)
        hm.addAction(about)
        disc = QAction("Discord", self)
        disc.triggered.connect(self.logic.open_discord)
        hm.addAction(disc)

    def init_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)

        lay = QVBoxLayout(cw)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self._build_typing_group(lay)

        human_row = QHBoxLayout()
        human_row.setSpacing(10)
        # why: keep all "humanization" features aligned and compact on a single row
        human_row.addWidget(self._build_errors_group())
        human_row.addWidget(self._build_breaks_group())
        human_row.addWidget(self._build_simulate_pauses_group())
        human_row.setStretch(0, 1)
        human_row.setStretch(1, 1)
        human_row.setStretch(2, 1)
        lay.addLayout(human_row)

        self._build_text_group(lay)
        self._build_profiles_group(lay)
        self._build_ads_footer(lay)

    def _build_typing_group(self, parent_layout: QVBoxLayout) -> None:
        tb = QGroupBox("Typing")
        tb_lay = QVBoxLayout(tb)
        tb_lay.setContentsMargins(12, 10, 12, 10)
        tb_lay.setSpacing(6)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        hotkey_lab = QLabel("Hotkey:")
        self.fk = QComboBox()
        self.fk.addItems(FUNCTION_KEYS)
        self.fk.currentTextChanged.connect(self.on_fkey_changed)

        wpm_lab = QLabel("WPM:")
        self.wpm_e = QLineEdit(str(self.default_wpm))
        self.wpm_e.setFixedWidth(70)
        self.wpm_e.setAlignment(Qt.AlignRight)
        self.wpm_e.setValidator(QIntValidator(WPM_MIN, WPM_MAX, self))
        self.wpm_e.textChanged.connect(self.on_wpm_changed)
        self.wpm_e.editingFinished.connect(self.on_wpm_editing_finished)

        self.stop_after_cb = QCheckBox("Stop after")
        self.stop_after_cb.setChecked(self.default_stop_after_enabled)
        self.stop_after_cb.setToolTip("Automatically stop typing after the specified number of seconds.")
        self.stop_after_cb.toggled.connect(self.on_toggled_stop_after)

        self.stop_after_e = QLineEdit(str(self.default_stop_after_seconds))
        self.stop_after_e.setFixedWidth(70)
        self.stop_after_e.setAlignment(Qt.AlignRight)
        self.stop_after_e.setValidator(QIntValidator(1, 86400, self))
        self.stop_after_e.editingFinished.connect(self.on_stop_after_editing_finished)

        stop_after_suffix = QLabel("s")
        stop_after_suffix.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.delay_cb = QCheckBox("Delay 2s")
        self.delay_cb.setToolTip("Wait 2 seconds before starting to type.")

        self.sticky_cb = QCheckBox("Sticky typing")
        self.sticky_cb.setChecked(self.default_sticky_typing)
        self.sticky_cb.setToolTip(
            "When enabled, AutoQuill keeps typing into the window/control that was focused when typing started."
        )

        toggles = QHBoxLayout()
        toggles.setSpacing(10)
        toggles.addStretch(1)
        toggles.addWidget(self.stop_after_cb)
        toggles.addWidget(self.stop_after_e)
        toggles.addWidget(stop_after_suffix)
        toggles.addSpacing(10)
        toggles.addWidget(self.delay_cb)
        toggles.addWidget(self.sticky_cb)

        self.loop_cb = QCheckBox("Loop")
        self.loop_cb.toggled.connect(self.on_toggled_loop)

        wait_lab = QLabel("Wait:")
        self.min_e = QLineEdit("5")
        self.min_e.setFixedWidth(60)
        self.min_e.setAlignment(Qt.AlignCenter)

        dash = QLabel("–")
        dash.setAlignment(Qt.AlignCenter)

        self.max_e = QLineEdit("10")
        self.max_e.setFixedWidth(60)
        self.max_e.setAlignment(Qt.AlignCenter)

        sec_lab = QLabel("s")
        sec_lab.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        wait_row = QHBoxLayout()
        wait_row.setSpacing(6)
        wait_row.addStretch(1)
        wait_row.addWidget(wait_lab)
        wait_row.addWidget(self.min_e)
        wait_row.addWidget(dash)
        wait_row.addWidget(self.max_e)
        wait_row.addWidget(sec_lab)

        grid.addWidget(hotkey_lab, 0, 0)
        grid.addWidget(self.fk, 0, 1)
        grid.addWidget(wpm_lab, 0, 2)
        grid.addWidget(self.wpm_e, 0, 3)
        grid.addLayout(toggles, 0, 4)

        grid.addWidget(self.loop_cb, 1, 0)
        grid.addLayout(wait_row, 1, 1, 1, 4)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)

        tb_lay.addLayout(grid)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        status_lab = QLabel("Status:")
        self.status_val = QLabel("Idle")

        self.progress_val = QLabel("Typed 0/0 chars • ETA --:--")

        hint = "Hotkey starts typing; during typing it toggles Pause/Resume. Press Esc to Stop."
        self.status_val.setToolTip(hint)
        self.progress_val.setToolTip(hint)

        status_row.addWidget(status_lab)
        status_row.addWidget(self.status_val)
        status_row.addStretch(1)
        status_row.addWidget(self.progress_val)

        tb_lay.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(10)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        tb_lay.addWidget(self.progress_bar)

        parent_layout.addWidget(tb)

        self.on_toggled_loop(self.loop_cb.isChecked())
        self.on_toggled_stop_after(self.stop_after_cb.isChecked())

    def _build_breaks_group(self) -> QGroupBox:
        br = QGroupBox("Simulate Breaks")
        br.setCheckable(True)
        br.setToolTip("Simulate Breaks: Longer pauses based on a word-count range.")

        br_lay = QGridLayout(br)
        br_lay.setContentsMargins(12, 10, 12, 10)
        br_lay.setHorizontalSpacing(10)
        br_lay.setVerticalSpacing(8)

        every_lab = QLabel("Every:")
        self.break_words_min_e = QLineEdit(str(self.default_breaks_word_min))
        self.break_words_min_e.setFixedWidth(60)
        self.break_words_min_e.setAlignment(Qt.AlignCenter)

        dash1 = QLabel("–")
        dash1.setAlignment(Qt.AlignCenter)

        self.break_words_max_e = QLineEdit(str(self.default_breaks_word_max))
        self.break_words_max_e.setFixedWidth(60)
        self.break_words_max_e.setAlignment(Qt.AlignCenter)

        words_suffix = QLabel("words")

        pause_lab = QLabel("Pause:")
        self.break_secs_min_e = QLineEdit(str(self.default_breaks_sec_min))
        self.break_secs_min_e.setFixedWidth(60)
        self.break_secs_min_e.setAlignment(Qt.AlignCenter)

        dash2 = QLabel("–")
        dash2.setAlignment(Qt.AlignCenter)

        self.break_secs_max_e = QLineEdit(str(self.default_breaks_sec_max))
        self.break_secs_max_e.setFixedWidth(60)
        self.break_secs_max_e.setAlignment(Qt.AlignCenter)

        secs_suffix = QLabel("s")

        br_lay.addWidget(every_lab, 0, 0)
        br_lay.addWidget(self.break_words_min_e, 0, 1)
        br_lay.addWidget(dash1, 0, 2)
        br_lay.addWidget(self.break_words_max_e, 0, 3)
        br_lay.addWidget(words_suffix, 0, 4)

        br_lay.addWidget(pause_lab, 1, 0)
        br_lay.addWidget(self.break_secs_min_e, 1, 1)
        br_lay.addWidget(dash2, 1, 2)
        br_lay.addWidget(self.break_secs_max_e, 1, 3)
        br_lay.addWidget(secs_suffix, 1, 4)

        br_lay.setColumnStretch(5, 1)

        self.breaks_cb = br
        self.breaks_cb.toggled.connect(self.on_toggled_breaks)
        self.breaks_cb.setChecked(self.default_breaks_enabled)
        self.on_toggled_breaks(self.breaks_cb.isChecked())

        return br

    def _build_errors_group(self) -> QGroupBox:
        err_box = QGroupBox("Simulate Errors")
        err_box.setCheckable(True)
        err_box.setToolTip("Simulate Errors: Occasional typos + backspace corrections.")

        err_lay = QGridLayout(err_box)
        err_lay.setContentsMargins(12, 10, 12, 10)
        err_lay.setHorizontalSpacing(10)
        err_lay.setVerticalSpacing(8)

        every_lab = QLabel("Every:")
        self.mi_e = QLineEdit(str(self.default_min_interval))
        self.mi_e.setFixedWidth(60)
        self.mi_e.setAlignment(Qt.AlignCenter)

        dash1 = QLabel("–")
        dash1.setAlignment(Qt.AlignCenter)

        self.ma_e = QLineEdit(str(self.default_max_interval))
        self.ma_e.setFixedWidth(60)
        self.ma_e.setAlignment(Qt.AlignCenter)

        chars_suffix = QLabel("chars")

        typos_lab = QLabel("Typos:")
        self.me_e = QLineEdit(str(self.default_min_errors))
        self.me_e.setFixedWidth(60)
        self.me_e.setAlignment(Qt.AlignCenter)

        dash2 = QLabel("–")
        dash2.setAlignment(Qt.AlignCenter)

        self.mx_e = QLineEdit(str(self.default_max_errors))
        self.mx_e.setFixedWidth(60)
        self.mx_e.setAlignment(Qt.AlignCenter)

        typos_suffix = QLabel("count")

        err_lay.addWidget(every_lab, 0, 0)
        err_lay.addWidget(self.mi_e, 0, 1)
        err_lay.addWidget(dash1, 0, 2)
        err_lay.addWidget(self.ma_e, 0, 3)
        err_lay.addWidget(chars_suffix, 0, 4)

        err_lay.addWidget(typos_lab, 1, 0)
        err_lay.addWidget(self.me_e, 1, 1)
        err_lay.addWidget(dash2, 1, 2)
        err_lay.addWidget(self.mx_e, 1, 3)
        err_lay.addWidget(typos_suffix, 1, 4)

        err_lay.setColumnStretch(5, 1)

        self.err_cb = err_box
        self.err_cb.toggled.connect(self.on_toggled_simulate_errors)
        self.err_cb.setChecked(False)
        self.on_toggled_simulate_errors(self.err_cb.isChecked())

        return err_box

    def _build_simulate_pauses_group(self) -> QGroupBox:
        pauses = QGroupBox("Simulate Pauses")
        pauses.setCheckable(True)
        pauses.setToolTip("Simulate Pauses: Short pauses every N characters.")

        lay = QGridLayout(pauses)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setHorizontalSpacing(10)
        lay.setVerticalSpacing(8)

        every_lab = QLabel("Every:")
        self.pause_every_min_e = QLineEdit(str(self.default_pause_every_min_chars))
        self.pause_every_min_e.setFixedWidth(60)
        self.pause_every_min_e.setAlignment(Qt.AlignCenter)
        self.pause_every_min_e.setValidator(QIntValidator(1, 999999, self))

        dash1 = QLabel("–")
        dash1.setAlignment(Qt.AlignCenter)

        self.pause_every_max_e = QLineEdit(str(self.default_pause_every_max_chars))
        self.pause_every_max_e.setFixedWidth(60)
        self.pause_every_max_e.setAlignment(Qt.AlignCenter)
        self.pause_every_max_e.setValidator(QIntValidator(1, 999999, self))

        chars_suffix = QLabel("chars")

        pause_lab = QLabel("Pause:")
        self.pause_secs_min_e = QLineEdit(str(self.default_pause_min_seconds))
        self.pause_secs_min_e.setFixedWidth(60)
        self.pause_secs_min_e.setAlignment(Qt.AlignCenter)
        self.pause_secs_min_e.setValidator(QDoubleValidator(0.0, 60.0, 2, self))

        dash2 = QLabel("–")
        dash2.setAlignment(Qt.AlignCenter)

        self.pause_secs_max_e = QLineEdit(str(self.default_pause_max_seconds))
        self.pause_secs_max_e.setFixedWidth(60)
        self.pause_secs_max_e.setAlignment(Qt.AlignCenter)
        self.pause_secs_max_e.setValidator(QDoubleValidator(0.0, 60.0, 2, self))

        secs_suffix = QLabel("s")

        lay.addWidget(every_lab, 0, 0)
        lay.addWidget(self.pause_every_min_e, 0, 1)
        lay.addWidget(dash1, 0, 2)
        lay.addWidget(self.pause_every_max_e, 0, 3)
        lay.addWidget(chars_suffix, 0, 4)

        lay.addWidget(pause_lab, 1, 0)
        lay.addWidget(self.pause_secs_min_e, 1, 1)
        lay.addWidget(dash2, 1, 2)
        lay.addWidget(self.pause_secs_max_e, 1, 3)
        lay.addWidget(secs_suffix, 1, 4)

        lay.setColumnStretch(5, 1)

        self.sim_pauses_cb = pauses
        self.sim_pauses_cb.toggled.connect(self.on_toggled_simulate_pauses)
        self.sim_pauses_cb.setChecked(self.default_simulate_pauses_enabled)
        self.on_toggled_simulate_pauses(self.sim_pauses_cb.isChecked())

        return pauses

    def _build_text_group(self, parent_layout: QVBoxLayout) -> None:
        text_box = QGroupBox("Text to type")
        text_lay = QVBoxLayout(text_box)
        text_lay.setContentsMargins(12, 10, 12, 10)
        text_lay.setSpacing(8)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter text to type (plain text only)...")
        text_lay.addWidget(self.text_edit)

        parent_layout.addWidget(text_box, 1)

    def _build_profiles_group(self, parent_layout: QVBoxLayout) -> None:
        profiles = QGroupBox("Profiles")
        p_lay = QHBoxLayout(profiles)
        p_lay.setContentsMargins(12, 10, 12, 10)
        p_lay.setSpacing(10)

        left = QHBoxLayout()
        left.setSpacing(10)

        name_lab = QLabel("Name:")
        self.save_name_e = QLineEdit()
        self.save_name_e.setPlaceholderText("Save name")
        self.save_name_e.setFixedWidth(170)

        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(90)
        self.save_btn.clicked.connect(self.on_save_clicked)

        left.addWidget(name_lab)
        left.addWidget(self.save_name_e)
        left.addWidget(self.save_btn)

        right = QHBoxLayout()
        right.setSpacing(10)

        saved_lab = QLabel("Saved:")
        self.saves_combo = QComboBox()
        self.saves_combo.setMinimumWidth(180)

        self.load_btn = QPushButton("Load")
        self.load_btn.setFixedWidth(90)
        self.load_btn.clicked.connect(self.on_load_clicked)

        right.addWidget(saved_lab)
        right.addWidget(self.saves_combo)
        right.addWidget(self.load_btn)

        p_lay.addLayout(left)
        p_lay.addStretch(1)
        p_lay.addLayout(right)

        parent_layout.addWidget(profiles)

    def _build_ads_footer(self, parent_layout: QVBoxLayout) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        parent_layout.addWidget(sep)

        self.ad_view = create_adsense_view()
        parent_layout.addWidget(self.ad_view, alignment=Qt.AlignHCenter)
        load_adsense_content(self.ad_view)

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

    @staticmethod
    def _format_mm_ss(seconds: int) -> str:
        if seconds < 0:
            seconds = 0
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def on_toggled_breaks(self, checked: bool):
        for w in (
            self.break_words_min_e,
            self.break_words_max_e,
            self.break_secs_min_e,
            self.break_secs_max_e,
        ):
            w.setEnabled(checked)

    def on_toggled_loop(self, checked: bool):
        self.min_e.setEnabled(checked)
        self.max_e.setEnabled(checked)

    def on_toggled_stop_after(self, checked: bool):
        self.stop_after_e.setEnabled(checked)

    def on_stop_after_editing_finished(self):
        if not self.stop_after_cb.isChecked():
            return
        try:
            val = int(self.stop_after_e.text())
        except Exception:
            val = self.default_stop_after_seconds
        if val < 1:
            val = 1
        if val > 86400:
            val = 86400
        self.stop_after_e.setText(str(val))

    def on_toggled_simulate_errors(self, enabled: bool):
        self.simulate_human_errors = enabled
        for w in (self.mi_e, self.ma_e, self.me_e, self.mx_e):
            w.setEnabled(enabled)

    def on_toggled_simulate_pauses(self, enabled: bool):
        for w in (
            self.pause_every_min_e,
            self.pause_every_max_e,
            self.pause_secs_min_e,
            self.pause_secs_max_e,
        ):
            w.setEnabled(enabled)

    def refresh_save_list(self):
        names = self.logic.list_save_files()
        self.saves_combo.blockSignals(True)
        self.saves_combo.clear()
        self.saves_combo.addItems(names)
        self.saves_combo.blockSignals(False)

    def on_save_clicked(self):
        name = self.save_name_e.text().strip()
        if not name:
            QMessageBox.warning(self, "Save failed", "Please enter a file name.")
            return
        if any(c in r'<>:"/\|?*' for c in name):
            QMessageBox.warning(self, "Save failed", "File name contains invalid characters.")
            return
        self.logic.save_config(name)
        self.refresh_save_list()
        self.saves_combo.setCurrentText(name)

    def on_load_clicked(self):
        name = self.saves_combo.currentText().strip()
        if not name:
            return
        if self.logic.load_config(name):
            self.refresh_save_list()
        else:
            QMessageBox.warning(self, "Load failed", "Selected configuration is invalid or missing.")

    def on_fkey_changed(self, t):
        self.function_key = t
        self.function_key_lower = t.lower()

    def on_wpm_changed(self, t: str):
        try:
            self.wpm = int(t)
        except Exception:
            pass

    def on_wpm_editing_finished(self):
        try:
            val = int(self.wpm_e.text())
        except Exception:
            val = self.default_wpm
        val = max(WPM_MIN, min(WPM_MAX, val))
        self.wpm = val
        self.wpm_e.setText(str(val))

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
