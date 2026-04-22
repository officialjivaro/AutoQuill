# appdata/ui/dialogs/typing_settings_dialog.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from appdata.core.configs.constants import APP_NAME, FUNCTION_KEYS, WPM_MAX, WPM_MIN
from appdata.core.settings.typing_settings_logic import TypingSettingsLogic
from appdata.ui.themes.app_theme import apply_app_theme, set_widget_role, set_widget_state


class TypingSettingsDialog(QDialog):
    """
    Settings dialog for the auto-typer.

    This is the renamed long-term home of the settings UI.
    The non-visual settings behavior still lives in TypingSettingsLogic for now.
    """

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.logic = TypingSettingsLogic(self)

        # Track the most recently saved/loaded profile so the main window can
        # show a meaningful summary without guessing from the combo box alone.
        self.current_profile_name = ""

        self.setObjectName("SettingsDialogRoot")
        self.setWindowTitle(f"{APP_NAME} Settings")
        self.resize(780, 560)

        apply_app_theme(self)
        self._build_ui()
        self._connect_warning_refreshes()
        self.logic.sync_runtime_attrs()
        self.refresh_save_list()
        self._refresh_warnings()

    def _make_int_edit(
        self,
        text: str,
        minimum: int,
        maximum: int,
        *,
        width: int = 60,
        align=Qt.AlignCenter,
    ) -> QLineEdit:
        edit = QLineEdit(text)
        edit.setFixedWidth(width)
        edit.setAlignment(align)
        edit.setValidator(QIntValidator(minimum, maximum, self))
        return edit

    def _make_float_edit(
        self,
        text: str,
        minimum: float,
        maximum: float,
        decimals: int,
        *,
        width: int = 60,
        align=Qt.AlignCenter,
    ) -> QLineEdit:
        edit = QLineEdit(text)
        edit.setFixedWidth(width)
        edit.setAlignment(align)
        edit.setValidator(QDoubleValidator(minimum, maximum, decimals, self))
        return edit

    @staticmethod
    def _make_dash_label() -> QLabel:
        dash = QLabel("–")
        dash.setAlignment(Qt.AlignCenter)
        return dash

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._build_typing_group(layout)

        human_row = QHBoxLayout()
        human_row.setSpacing(10)
        human_row.addWidget(self._build_errors_group())
        human_row.addWidget(self._build_breaks_group())
        human_row.addWidget(self._build_simulate_pauses_group())
        human_row.setStretch(0, 1)
        human_row.setStretch(1, 1)
        human_row.setStretch(2, 1)
        layout.addLayout(human_row)

        self._build_warnings_group(layout)
        self._build_profiles_group(layout)

        close_row = QHBoxLayout()
        close_row.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(close_btn, "secondary")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)

        layout.addLayout(close_row)

    def _build_typing_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Typing Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 10)
        group_layout.setSpacing(6)

        controls_widget = QWidget(group)
        grid = QGridLayout(controls_widget)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        hotkey_lab = QLabel("Hotkey:")
        hotkey_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.fk = QComboBox()
        self.fk.addItems(FUNCTION_KEYS)
        self.fk.setFixedWidth(100)
        self.fk.setCurrentText(self.host.function_key)
        self.fk.currentTextChanged.connect(self.on_fkey_changed)

        wpm_lab = QLabel("WPM:")
        wpm_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.wpm_e = self._make_int_edit(
            str(self.host.default_wpm),
            WPM_MIN,
            WPM_MAX,
            width=70,
            align=Qt.AlignRight,
        )
        self.wpm_e.setToolTip("Words per minute (standard: 5 characters per word).")
        self.wpm_e.textChanged.connect(self.on_wpm_changed)
        self.wpm_e.editingFinished.connect(self.on_wpm_editing_finished)

        self.stop_after_cb = QCheckBox("Stop after")
        self.stop_after_cb.setChecked(self.host.default_stop_after_enabled)
        self.stop_after_cb.setToolTip("Automatically stop typing after the specified number of seconds.")
        self.stop_after_cb.toggled.connect(self.on_toggled_stop_after)

        self.stop_after_e = self._make_int_edit(
            str(self.host.default_stop_after_seconds),
            1,
            86400,
            width=70,
            align=Qt.AlignRight,
        )
        self.stop_after_e.editingFinished.connect(self.on_stop_after_editing_finished)

        stop_after_suffix = QLabel("s")
        stop_after_suffix.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.delay_cb = QCheckBox("Start Delay")
        self.delay_cb.setToolTip("Wait 2 seconds before starting to type.")

        self.sticky_cb = QCheckBox("Sticky typing")
        self.sticky_cb.setChecked(self.host.default_sticky_typing)
        self.sticky_cb.setToolTip(
            "When enabled, AutoQuill keeps typing into the window/control that was focused when typing started."
        )

        self.loop_cb = QCheckBox("Loop")
        self.loop_cb.toggled.connect(self.on_toggled_loop)

        wait_lab = QLabel("Wait:")
        wait_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.min_e = self._make_int_edit("5", 1, 86400, align=Qt.AlignRight)
        self.max_e = self._make_int_edit("10", 1, 86400, align=Qt.AlignRight)

        sec_lab = QLabel("s")
        sec_lab.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        wait_row = QHBoxLayout()
        wait_row.setSpacing(6)
        wait_row.addWidget(wait_lab)
        wait_row.addWidget(self.min_e)
        wait_row.addWidget(self._make_dash_label())
        wait_row.addWidget(self.max_e)
        wait_row.addWidget(sec_lab)

        grid.setColumnMinimumWidth(2, 16)
        grid.setColumnMinimumWidth(5, 16)

        grid.addWidget(hotkey_lab, 0, 0)
        grid.addWidget(self.fk, 0, 1)
        grid.addWidget(wpm_lab, 0, 3)
        grid.addWidget(self.wpm_e, 0, 4)
        grid.addWidget(self.stop_after_cb, 0, 6)
        grid.addWidget(self.stop_after_e, 0, 7)
        grid.addWidget(stop_after_suffix, 0, 8)

        grid.addWidget(self.delay_cb, 1, 1)
        grid.addWidget(self.sticky_cb, 1, 4)
        grid.addWidget(self.loop_cb, 1, 6)

        grid.addLayout(wait_row, 2, 3, 1, 6)

        controls_center_row = QHBoxLayout()
        controls_center_row.addStretch(1)
        controls_center_row.addWidget(controls_widget)
        controls_center_row.addStretch(1)
        group_layout.addLayout(controls_center_row)

        parent_layout.addWidget(group)

        self.on_toggled_loop(self.loop_cb.isChecked())
        self.on_toggled_stop_after(self.stop_after_cb.isChecked())

    def _build_breaks_group(self) -> QGroupBox:
        group = QGroupBox("Simulate Breaks")
        group.setCheckable(True)
        group.setToolTip("Simulate Breaks: Longer pauses based on a word-count range.")

        layout = QGridLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        every_lab = QLabel("Every:")
        self.break_words_min_e = self._make_int_edit(
            str(self.host.default_breaks_word_min),
            1,
            999999,
        )
        self.break_words_max_e = self._make_int_edit(
            str(self.host.default_breaks_word_max),
            1,
            999999,
        )
        words_suffix = QLabel("words")

        pause_lab = QLabel("Pause:")
        self.break_secs_min_e = self._make_float_edit(
            str(self.host.default_breaks_sec_min),
            0.0,
            999999.0,
            2,
        )
        self.break_secs_max_e = self._make_float_edit(
            str(self.host.default_breaks_sec_max),
            0.0,
            999999.0,
            2,
        )
        secs_suffix = QLabel("s")

        layout.addWidget(every_lab, 0, 0)
        layout.addWidget(self.break_words_min_e, 0, 1)
        layout.addWidget(self._make_dash_label(), 0, 2)
        layout.addWidget(self.break_words_max_e, 0, 3)
        layout.addWidget(words_suffix, 0, 4)

        layout.addWidget(pause_lab, 1, 0)
        layout.addWidget(self.break_secs_min_e, 1, 1)
        layout.addWidget(self._make_dash_label(), 1, 2)
        layout.addWidget(self.break_secs_max_e, 1, 3)
        layout.addWidget(secs_suffix, 1, 4)

        layout.setColumnStretch(5, 1)

        self.breaks_cb = group
        self.breaks_cb.toggled.connect(self.on_toggled_breaks)
        self.breaks_cb.setChecked(self.host.default_breaks_enabled)
        self.on_toggled_breaks(self.breaks_cb.isChecked())

        return group

    def _build_errors_group(self) -> QGroupBox:
        group = QGroupBox("Simulate Errors")
        group.setCheckable(True)
        group.setToolTip("Simulate Errors: Occasional typos + backspace corrections.")

        layout = QGridLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        every_lab = QLabel("Every:")
        self.mi_e = self._make_int_edit(str(self.host.default_min_interval), 1, 999999)
        self.ma_e = self._make_int_edit(str(self.host.default_max_interval), 1, 999999)
        chars_suffix = QLabel("chars")

        typos_lab = QLabel("Typos:")
        self.me_e = self._make_int_edit(str(self.host.default_min_errors), 1, 999999)
        self.mx_e = self._make_int_edit(str(self.host.default_max_errors), 1, 999999)
        typos_suffix = QLabel("count")

        layout.addWidget(every_lab, 0, 0)
        layout.addWidget(self.mi_e, 0, 1)
        layout.addWidget(self._make_dash_label(), 0, 2)
        layout.addWidget(self.ma_e, 0, 3)
        layout.addWidget(chars_suffix, 0, 4)

        layout.addWidget(typos_lab, 1, 0)
        layout.addWidget(self.me_e, 1, 1)
        layout.addWidget(self._make_dash_label(), 1, 2)
        layout.addWidget(self.mx_e, 1, 3)
        layout.addWidget(typos_suffix, 1, 4)

        layout.setColumnStretch(5, 1)

        self.err_cb = group
        self.err_cb.toggled.connect(self.on_toggled_simulate_errors)
        self.err_cb.setChecked(False)
        self.on_toggled_simulate_errors(self.err_cb.isChecked())

        return group

    def _build_simulate_pauses_group(self) -> QGroupBox:
        group = QGroupBox("Simulate Pauses")
        group.setCheckable(True)
        group.setToolTip("Simulate Pauses: Short pauses every N characters.")

        layout = QGridLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        every_lab = QLabel("Every:")
        self.pause_every_min_e = self._make_int_edit(
            str(self.host.default_pause_every_min_chars),
            1,
            999999,
        )
        self.pause_every_max_e = self._make_int_edit(
            str(self.host.default_pause_every_max_chars),
            1,
            999999,
        )
        chars_suffix = QLabel("chars")

        pause_lab = QLabel("Pause:")
        self.pause_secs_min_e = self._make_float_edit(
            str(self.host.default_pause_min_seconds),
            0.0,
            60.0,
            2,
        )
        self.pause_secs_max_e = self._make_float_edit(
            str(self.host.default_pause_max_seconds),
            0.0,
            60.0,
            2,
        )
        secs_suffix = QLabel("s")

        layout.addWidget(every_lab, 0, 0)
        layout.addWidget(self.pause_every_min_e, 0, 1)
        layout.addWidget(self._make_dash_label(), 0, 2)
        layout.addWidget(self.pause_every_max_e, 0, 3)
        layout.addWidget(chars_suffix, 0, 4)

        layout.addWidget(pause_lab, 1, 0)
        layout.addWidget(self.pause_secs_min_e, 1, 1)
        layout.addWidget(self._make_dash_label(), 1, 2)
        layout.addWidget(self.pause_secs_max_e, 1, 3)
        layout.addWidget(secs_suffix, 1, 4)

        layout.setColumnStretch(5, 1)

        self.sim_pauses_cb = group
        self.sim_pauses_cb.toggled.connect(self.on_toggled_simulate_pauses)
        self.sim_pauses_cb.setChecked(self.host.default_simulate_pauses_enabled)
        self.on_toggled_simulate_pauses(self.sim_pauses_cb.isChecked())

        return group

    def _build_warnings_group(self, parent_layout: QVBoxLayout) -> None:
        self.warnings_box = QGroupBox("Warnings")
        self.warnings_box.setObjectName("WarningsBox")

        warnings_layout = QVBoxLayout(self.warnings_box)
        warnings_layout.setContentsMargins(12, 10, 12, 10)
        warnings_layout.setSpacing(6)

        self.warning_text_val = QLabel("No warnings right now.")
        self.warning_text_val.setObjectName("WarningsValue")
        self.warning_text_val.setWordWrap(True)
        self.warning_text_val.setTextFormat(Qt.RichText)
        set_widget_state(self.warning_text_val, "normal")

        warnings_layout.addWidget(self.warning_text_val)
        parent_layout.addWidget(self.warnings_box)

    def _build_profiles_group(self, parent_layout: QVBoxLayout) -> None:
        profiles = QGroupBox("Profiles")
        layout = QHBoxLayout(profiles)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        left = QHBoxLayout()
        left.setSpacing(10)

        name_lab = QLabel("Name:")
        self.save_name_e = QLineEdit()
        self.save_name_e.setPlaceholderText("Save name")
        self.save_name_e.setFixedWidth(170)

        self.save_btn = QPushButton("Save")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(self.save_btn, "primary")
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
        self.load_btn.setCursor(Qt.PointingHandCursor)
        set_widget_role(self.load_btn, "secondary")
        self.load_btn.setFixedWidth(90)
        self.load_btn.clicked.connect(self.on_load_clicked)

        right.addWidget(saved_lab)
        right.addWidget(self.saves_combo)
        right.addWidget(self.load_btn)

        layout.addLayout(left)
        layout.addStretch(1)
        layout.addLayout(right)

        parent_layout.addWidget(profiles)

    def _connect_warning_refreshes(self) -> None:
        """
        Refresh warnings live when the user changes settings or the main text.
        """
        warning_toggles = (
            self.loop_cb,
            self.stop_after_cb,
            self.breaks_cb,
            self.sim_pauses_cb,
        )
        for checkbox in warning_toggles:
            checkbox.toggled.connect(self._refresh_warnings)

        warning_fields = (
            self.wpm_e,
            self.stop_after_e,
            self.min_e,
            self.max_e,
            self.break_words_min_e,
            self.break_words_max_e,
            self.break_secs_min_e,
            self.break_secs_max_e,
            self.pause_every_min_e,
            self.pause_every_max_e,
            self.pause_secs_min_e,
            self.pause_secs_max_e,
        )
        for field in warning_fields:
            field.textChanged.connect(self._refresh_warnings)

        self.host.text_edit.textChanged.connect(self._refresh_warnings)

    def _refresh_warnings(self) -> None:
        warnings = self.logic.get_live_warnings()
        if warnings:
            html = "<br>".join(f"• {warning}" for warning in warnings)
            self.warning_text_val.setText(html)
            set_widget_state(self.warning_text_val, "warning")
        else:
            self.warning_text_val.setText("No warnings right now.")
            set_widget_state(self.warning_text_val, "normal")

    def _get_profile_display_name(self) -> str:
        """
        Return the best user-facing profile label for the main-window summary.

        We only treat a profile as "current" after a successful save or load,
        otherwise the summary falls back to "Unsaved".
        """
        current_name = self.current_profile_name.strip()
        return current_name if current_name else "Unsaved"

    def get_profile_switch_state(self) -> dict:
        """
        Return the profile names and current profile for the main-window quick switch.
        """
        names = [self.saves_combo.itemText(i) for i in range(self.saves_combo.count())]
        return {
            "names": names,
            "current_name": self.current_profile_name.strip(),
        }

    def get_header_summary(self) -> dict:
        """
        Return a small, display-ready summary for the main window header.
        """
        settings = self.get_runtime_settings()
        profile_name = self._get_profile_display_name()

        summary_text = (
            f"Hotkey {settings['function_key']} • "
            f"{settings['wpm']} WPM • "
            f"Sticky {'On' if settings['sticky_typing'] else 'Off'} • "
            f"Loop {'On' if settings['loop_enabled'] else 'Off'} • "
            f"Profile: {profile_name}"
        )
        return {
            "summary_text": summary_text,
            "profile_name": profile_name,
            "function_key": settings["function_key"],
            "wpm": settings["wpm"],
            "sticky_typing": settings["sticky_typing"],
        }

    def load_profile_by_name(self, name: str) -> bool:
        """
        Load a saved profile from either the dialog or the main-window quick switch.
        """
        profile_name = name.strip()
        if not profile_name:
            return False

        if self.host.logic.load_config(profile_name):
            self.current_profile_name = profile_name
            self.refresh_save_list()
            self.saves_combo.setCurrentText(profile_name)
            self.save_name_e.setText(profile_name)
            self._refresh_warnings()
            return True
        return False

    # These public pass-through methods keep the dialog API stable while the
    # behavior stays in TypingSettingsLogic.
    def get_runtime_settings(self) -> dict:
        return self.logic.get_runtime_settings()

    def collect_config(self, typing_text: str) -> dict:
        return self.logic.collect_config(typing_text)

    def apply_config(self, config: dict) -> None:
        self.logic.apply_config(config)
        self._refresh_warnings()

    def refresh_save_list(self):
        self.logic.refresh_save_list()

        if self.current_profile_name:
            self.saves_combo.setCurrentText(self.current_profile_name)
        self._refresh_warnings()

    def on_save_clicked(self):
        name = self.save_name_e.text().strip()
        error_message = self.logic.validate_save_name(name)
        if error_message:
            QMessageBox.warning(self, "Save failed", error_message)
            return

        self.host.logic.save_config(name)
        self.current_profile_name = name
        self.refresh_save_list()
        self.saves_combo.setCurrentText(name)

    def on_load_clicked(self):
        name = self.saves_combo.currentText().strip()
        if not name:
            return

        if not self.load_profile_by_name(name):
            QMessageBox.warning(self, "Load failed", "Selected configuration is invalid or missing.")

    def on_fkey_changed(self, text):
        self.logic.handle_hotkey_changed(text)

    def on_wpm_changed(self, text: str):
        self.logic.handle_wpm_changed(text)

    def on_wpm_editing_finished(self):
        self.logic.clamp_wpm_field()

    def on_toggled_breaks(self, checked: bool):
        self.logic.set_break_controls_enabled(checked)

    def on_toggled_loop(self, checked: bool):
        self.logic.set_loop_controls_enabled(checked)

    def on_toggled_stop_after(self, checked: bool):
        self.logic.set_stop_after_controls_enabled(checked)

    def on_stop_after_editing_finished(self):
        self.logic.clamp_stop_after_field()

    def on_toggled_simulate_errors(self, enabled: bool):
        self.logic.set_error_controls_enabled(enabled)

    def on_toggled_simulate_pauses(self, enabled: bool):
        self.logic.set_pause_controls_enabled(enabled)