# appdata/core/typing_settings_logic.py
from appdata.core.configs.constants import FUNCTION_KEYS, WPM_MAX, WPM_MIN


_INVALID_SAVE_NAME_CHARS = set(r'<>:"/\|?*')


class TypingSettingsLogic:
    """
    Non-visual behavior for the typing settings dialog.

    This keeps parsing, validation, value normalization, warning generation,
    and config application separate from the widget-building code.
    """

    def __init__(self, dialog):
        self.dialog = dialog
        self.host = dialog.host

    @staticmethod
    def _coerce_int(raw, default: int, minimum=None, maximum=None) -> int:
        try:
            value = int(raw)
        except Exception:
            value = int(default)

        if minimum is not None and value < minimum:
            value = minimum
        if maximum is not None and value > maximum:
            value = maximum
        return value

    @staticmethod
    def _coerce_float(raw, default: float, minimum=None, maximum=None) -> float:
        try:
            value = float(raw)
        except Exception:
            value = float(default)

        if minimum is not None and value < minimum:
            value = minimum
        if maximum is not None and value > maximum:
            value = maximum
        return value

    @staticmethod
    def _coerce_bool(raw, default: bool) -> bool:
        return raw if isinstance(raw, bool) else default

    @staticmethod
    def _try_int(raw) -> int | None:
        try:
            return int(raw)
        except Exception:
            return None

    @staticmethod
    def _try_float(raw) -> float | None:
        try:
            return float(raw)
        except Exception:
            return None

    def _normalize_int_pair(
        self,
        raw_min,
        raw_max,
        default_min: int,
        default_max: int,
        *,
        minimum=None,
        maximum=None,
    ) -> tuple[int, int]:
        min_value = self._coerce_int(raw_min, default_min, minimum=minimum, maximum=maximum)
        max_value = self._coerce_int(raw_max, default_max, minimum=minimum, maximum=maximum)

        if min_value > max_value:
            min_value, max_value = max_value, min_value

        return min_value, max_value

    def _normalize_float_pair(
        self,
        raw_min,
        raw_max,
        default_min: float,
        default_max: float,
        *,
        minimum=None,
        maximum=None,
    ) -> tuple[float, float]:
        min_value = self._coerce_float(raw_min, default_min, minimum=minimum, maximum=maximum)
        max_value = self._coerce_float(raw_max, default_max, minimum=minimum, maximum=maximum)

        if min_value > max_value:
            min_value, max_value = max_value, min_value

        return min_value, max_value

    def sync_runtime_attrs(self) -> None:
        self.host.function_key = self.dialog.fk.currentText()
        self.host.function_key_lower = self.host.function_key.lower()

        try:
            self.host.wpm = int(self.dialog.wpm_e.text())
        except Exception:
            self.host.wpm = self.host.default_wpm

        self.host.simulate_human_errors = self.dialog.err_cb.isChecked()

    def refresh_save_list(self) -> None:
        names = self.host.logic.list_save_files()
        combo = self.dialog.saves_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(names)
        combo.blockSignals(False)

    def validate_save_name(self, name: str) -> str | None:
        if not name:
            return "Please enter a file name."

        if any(char in _INVALID_SAVE_NAME_CHARS for char in name):
            return "File name contains invalid characters."

        return None

    def handle_hotkey_changed(self, text: str) -> None:
        self.host.function_key = text
        self.host.function_key_lower = text.lower()

    def handle_wpm_changed(self, text: str) -> None:
        try:
            self.host.wpm = int(text)
        except Exception:
            pass

    def clamp_wpm_field(self) -> None:
        wpm = self._coerce_int(
            self.dialog.wpm_e.text(),
            self.host.default_wpm,
            minimum=WPM_MIN,
            maximum=WPM_MAX,
        )
        self.host.wpm = wpm
        self.dialog.wpm_e.setText(str(wpm))

    def set_break_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.dialog.break_words_min_e,
            self.dialog.break_words_max_e,
            self.dialog.break_secs_min_e,
            self.dialog.break_secs_max_e,
        ):
            widget.setEnabled(enabled)

    def set_loop_controls_enabled(self, enabled: bool) -> None:
        self.dialog.min_e.setEnabled(enabled)
        self.dialog.max_e.setEnabled(enabled)

    def set_stop_after_controls_enabled(self, enabled: bool) -> None:
        self.dialog.stop_after_e.setEnabled(enabled)

    def clamp_stop_after_field(self) -> None:
        if not self.dialog.stop_after_cb.isChecked():
            return

        value = self._coerce_int(
            self.dialog.stop_after_e.text(),
            self.host.default_stop_after_seconds,
            minimum=1,
            maximum=86400,
        )
        self.dialog.stop_after_e.setText(str(value))

    def set_error_controls_enabled(self, enabled: bool) -> None:
        self.host.simulate_human_errors = enabled
        for widget in (
            self.dialog.mi_e,
            self.dialog.ma_e,
            self.dialog.me_e,
            self.dialog.mx_e,
        ):
            widget.setEnabled(enabled)

    def set_pause_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.dialog.pause_every_min_e,
            self.dialog.pause_every_max_e,
            self.dialog.pause_secs_min_e,
            self.dialog.pause_secs_max_e,
        ):
            widget.setEnabled(enabled)

    def get_live_warnings(self) -> list[str]:
        """
        Return a plain-English list of non-blocking warnings for confusing or
        risky settings combinations. These warnings do not change behavior;
        they only help the user understand what may happen.
        """
        warnings: list[str] = []

        raw_wpm = self._try_int(self.dialog.wpm_e.text())
        if raw_wpm is not None and raw_wpm >= 140:
            warnings.append(
                "Very high WPM can look less human and may type less reliably in some apps."
            )

        if self.dialog.stop_after_cb.isChecked():
            raw_stop_after = self._try_int(self.dialog.stop_after_e.text())
            if raw_stop_after is not None and raw_stop_after <= 5:
                warnings.append(
                    "Stop after is set very short. Typing may stop before much text is entered."
                )

        if self.dialog.loop_cb.isChecked():
            raw_loop_min = self._try_int(self.dialog.min_e.text())
            raw_loop_max = self._try_int(self.dialog.max_e.text())
            if (
                raw_loop_min is not None
                and raw_loop_max is not None
                and raw_loop_min > raw_loop_max
            ):
                warnings.append(
                    "Loop wait range is reversed. AutoQuill will swap the values when it runs."
                )

            if not self.host.text_edit.toPlainText().strip():
                warnings.append("Loop is enabled, but the main text box is empty.")

        if self.dialog.breaks_cb.isChecked():
            raw_break_words_min = self._try_int(self.dialog.break_words_min_e.text())
            raw_break_words_max = self._try_int(self.dialog.break_words_max_e.text())
            if (
                raw_break_words_min is not None
                and raw_break_words_max is not None
                and raw_break_words_min > raw_break_words_max
            ):
                warnings.append(
                    "Simulate Breaks word range is reversed. AutoQuill will swap the values when it runs."
                )

            raw_break_secs_min = self._try_float(self.dialog.break_secs_min_e.text())
            raw_break_secs_max = self._try_float(self.dialog.break_secs_max_e.text())
            if (
                raw_break_secs_min is not None
                and raw_break_secs_max is not None
                and raw_break_secs_min > raw_break_secs_max
            ):
                warnings.append(
                    "Simulate Breaks pause range is reversed. AutoQuill will swap the values when it runs."
                )

        if self.dialog.sim_pauses_cb.isChecked():
            raw_pause_every_min = self._try_int(self.dialog.pause_every_min_e.text())
            raw_pause_every_max = self._try_int(self.dialog.pause_every_max_e.text())
            if (
                raw_pause_every_min is not None
                and raw_pause_every_max is not None
                and raw_pause_every_min > raw_pause_every_max
            ):
                warnings.append(
                    "Simulate Pauses frequency range is reversed. AutoQuill will swap the values when it runs."
                )

            raw_pause_secs_min = self._try_float(self.dialog.pause_secs_min_e.text())
            raw_pause_secs_max = self._try_float(self.dialog.pause_secs_max_e.text())
            if (
                raw_pause_secs_min is not None
                and raw_pause_secs_max is not None
                and raw_pause_secs_min > raw_pause_secs_max
            ):
                warnings.append(
                    "Simulate Pauses duration range is reversed. AutoQuill will swap the values when it runs."
                )

        return warnings

    def _read_error_settings(self) -> dict:
        min_interval, max_interval = self._normalize_int_pair(
            self.dialog.mi_e.text(),
            self.dialog.ma_e.text(),
            self.host.default_min_interval,
            self.host.default_max_interval,
            minimum=1,
        )

        min_errors, max_errors = self._normalize_int_pair(
            self.dialog.me_e.text(),
            self.dialog.mx_e.text(),
            self.host.default_min_errors,
            self.host.default_max_errors,
            minimum=1,
        )

        return {
            "simulate_human_errors": self.dialog.err_cb.isChecked(),
            "min_interval": min_interval,
            "max_interval": max_interval,
            "min_errors": min_errors,
            "max_errors": max_errors,
        }

    def _read_loop_settings(self) -> dict:
        loop_min, loop_max = self._normalize_int_pair(
            self.dialog.min_e.text(),
            self.dialog.max_e.text(),
            5,
            10,
            minimum=1,
            maximum=86400,
        )

        return {
            "loop_enabled": self.dialog.loop_cb.isChecked(),
            "loop_min": loop_min,
            "loop_max": loop_max,
        }

    def _read_break_settings(self) -> dict:
        word_min, word_max = self._normalize_int_pair(
            self.dialog.break_words_min_e.text(),
            self.dialog.break_words_max_e.text(),
            self.host.default_breaks_word_min,
            self.host.default_breaks_word_max,
            minimum=1,
        )

        sec_min, sec_max = self._normalize_float_pair(
            self.dialog.break_secs_min_e.text(),
            self.dialog.break_secs_max_e.text(),
            self.host.default_breaks_sec_min,
            self.host.default_breaks_sec_max,
            minimum=0.0,
        )

        return {
            "breaks_enabled": self.dialog.breaks_cb.isChecked(),
            "breaks_word_min": word_min,
            "breaks_word_max": word_max,
            "breaks_sec_min": sec_min,
            "breaks_sec_max": sec_max,
        }

    def _read_pause_settings(self) -> dict:
        every_min, every_max = self._normalize_int_pair(
            self.dialog.pause_every_min_e.text(),
            self.dialog.pause_every_max_e.text(),
            self.host.default_pause_every_min_chars,
            self.host.default_pause_every_max_chars,
            minimum=1,
        )

        pause_min, pause_max = self._normalize_float_pair(
            self.dialog.pause_secs_min_e.text(),
            self.dialog.pause_secs_max_e.text(),
            self.host.default_pause_min_seconds,
            self.host.default_pause_max_seconds,
            minimum=0.0,
        )

        return {
            "simulate_pauses_enabled": self.dialog.sim_pauses_cb.isChecked(),
            "pause_every_min_chars": every_min,
            "pause_every_max_chars": every_max,
            "pause_min_seconds": pause_min,
            "pause_max_seconds": pause_max,
        }

    def _read_stop_after_settings(self) -> dict:
        stop_after_enabled = self._coerce_bool(
            self.dialog.stop_after_cb.isChecked(),
            self.host.default_stop_after_enabled,
        )

        stop_after_seconds = self._coerce_int(
            self.dialog.stop_after_e.text(),
            self.host.default_stop_after_seconds,
            minimum=1,
            maximum=86400,
        )

        return {
            "stop_after_enabled": stop_after_enabled,
            "stop_after_seconds": stop_after_seconds,
        }

    def get_runtime_settings(self) -> dict:
        """
        Return a normalized settings snapshot for typing, saving, and loading.
        """
        function_key = self.dialog.fk.currentText()
        if function_key not in FUNCTION_KEYS:
            function_key = self.host.function_key

        wpm = self._coerce_int(
            self.dialog.wpm_e.text(),
            self.host.default_wpm,
            minimum=WPM_MIN,
            maximum=WPM_MAX,
        )

        sticky_enabled = self._coerce_bool(
            self.dialog.sticky_cb.isChecked(),
            self.host.default_sticky_typing,
        )
        delay_before = self._coerce_bool(self.dialog.delay_cb.isChecked(), False)

        settings = {
            "function_key": function_key,
            "wpm": wpm,
            "sticky_typing": sticky_enabled,
            "delay_before": delay_before,
        }
        settings.update(self._read_stop_after_settings())
        settings.update(self._read_loop_settings())
        settings.update(self._read_pause_settings())
        settings.update(self._read_error_settings())
        settings.update(self._read_break_settings())

        # Keep the host in sync for live hotkey handling and any older callers.
        self.host.function_key = function_key
        self.host.function_key_lower = function_key.lower()
        self.host.wpm = wpm
        self.host.simulate_human_errors = settings["simulate_human_errors"]

        return settings

    def collect_config(self, typing_text: str) -> dict:
        config = self.get_runtime_settings()
        config["typing_text"] = typing_text
        return config

    def _apply_loop_settings(self, config: dict) -> None:
        loop_enabled = bool(config.get("loop_enabled", False))
        loop_min, loop_max = self._normalize_int_pair(
            config.get("loop_min", 5),
            config.get("loop_max", 10),
            5,
            10,
            minimum=1,
            maximum=86400,
        )

        self.dialog.loop_cb.setChecked(loop_enabled)
        self.dialog.min_e.setText(str(loop_min))
        self.dialog.max_e.setText(str(loop_max))
        self.set_loop_controls_enabled(self.dialog.loop_cb.isChecked())

    def _apply_stop_after_settings(self, config: dict) -> None:
        default_enabled = self.host.default_stop_after_enabled
        stop_after_enabled = config.get("stop_after_enabled", default_enabled)
        if not isinstance(stop_after_enabled, bool):
            stop_after_enabled = default_enabled

        stop_after_seconds = self._coerce_int(
            config.get("stop_after_seconds", self.host.default_stop_after_seconds),
            self.host.default_stop_after_seconds,
            minimum=1,
            maximum=86400,
        )

        self.dialog.stop_after_cb.setChecked(stop_after_enabled)
        self.dialog.stop_after_e.setText(str(stop_after_seconds))
        self.set_stop_after_controls_enabled(stop_after_enabled)

    def _apply_pause_settings(self, config: dict) -> None:
        default_enabled = self.host.default_simulate_pauses_enabled
        sim_pauses_enabled = config.get("simulate_pauses_enabled", default_enabled)
        if not isinstance(sim_pauses_enabled, bool):
            sim_pauses_enabled = default_enabled

        every_min, every_max = self._normalize_int_pair(
            config.get("pause_every_min_chars", self.host.default_pause_every_min_chars),
            config.get("pause_every_max_chars", self.host.default_pause_every_max_chars),
            self.host.default_pause_every_min_chars,
            self.host.default_pause_every_max_chars,
            minimum=1,
        )

        pause_min_s, pause_max_s = self._normalize_float_pair(
            config.get("pause_min_seconds", self.host.default_pause_min_seconds),
            config.get("pause_max_seconds", self.host.default_pause_max_seconds),
            self.host.default_pause_min_seconds,
            self.host.default_pause_max_seconds,
            minimum=0.0,
        )

        self.dialog.sim_pauses_cb.setChecked(sim_pauses_enabled)
        self.dialog.pause_every_min_e.setText(str(every_min))
        self.dialog.pause_every_max_e.setText(str(every_max))
        self.dialog.pause_secs_min_e.setText(str(pause_min_s))
        self.dialog.pause_secs_max_e.setText(str(pause_max_s))
        self.set_pause_controls_enabled(sim_pauses_enabled)

    def _apply_error_settings(self, config: dict) -> None:
        errors_enabled = bool(config.get("simulate_human_errors", False))

        min_interval, max_interval = self._normalize_int_pair(
            config.get("min_interval", self.host.default_min_interval),
            config.get("max_interval", self.host.default_max_interval),
            self.host.default_min_interval,
            self.host.default_max_interval,
            minimum=1,
        )

        min_errors, max_errors = self._normalize_int_pair(
            config.get("min_errors", self.host.default_min_errors),
            config.get("max_errors", self.host.default_max_errors),
            self.host.default_min_errors,
            self.host.default_max_errors,
            minimum=1,
        )

        self.dialog.err_cb.setChecked(errors_enabled)
        self.dialog.mi_e.setText(str(min_interval))
        self.dialog.ma_e.setText(str(max_interval))
        self.dialog.me_e.setText(str(min_errors))
        self.dialog.mx_e.setText(str(max_errors))
        self.set_error_controls_enabled(self.dialog.err_cb.isChecked())

    def _apply_break_settings(self, config: dict) -> None:
        breaks_enabled = bool(config.get("breaks_enabled", False))

        breaks_word_min, breaks_word_max = self._normalize_int_pair(
            config.get("breaks_word_min", self.host.default_breaks_word_min),
            config.get("breaks_word_max", self.host.default_breaks_word_max),
            self.host.default_breaks_word_min,
            self.host.default_breaks_word_max,
            minimum=1,
        )

        breaks_sec_min, breaks_sec_max = self._normalize_float_pair(
            config.get("breaks_sec_min", self.host.default_breaks_sec_min),
            config.get("breaks_sec_max", self.host.default_breaks_sec_max),
            self.host.default_breaks_sec_min,
            self.host.default_breaks_sec_max,
            minimum=0.0,
        )

        self.dialog.breaks_cb.setChecked(breaks_enabled)
        self.dialog.break_words_min_e.setText(str(breaks_word_min))
        self.dialog.break_words_max_e.setText(str(breaks_word_max))
        self.dialog.break_secs_min_e.setText(str(breaks_sec_min))
        self.dialog.break_secs_max_e.setText(str(breaks_sec_max))
        self.set_break_controls_enabled(self.dialog.breaks_cb.isChecked())

    def apply_config(self, config: dict) -> None:
        function_key = config.get("function_key", self.host.function_key)
        if function_key not in FUNCTION_KEYS:
            function_key = self.host.function_key
        self.dialog.fk.setCurrentText(function_key)

        wpm = self._coerce_int(
            config.get("wpm", self.host.default_wpm),
            self.host.default_wpm,
            minimum=WPM_MIN,
            maximum=WPM_MAX,
        )
        self.dialog.wpm_e.setText(str(wpm))
        self.host.wpm = wpm

        sticky_default = self.host.default_sticky_typing
        sticky = config.get("sticky_typing", sticky_default)
        if not isinstance(sticky, bool):
            sticky = sticky_default
        self.dialog.sticky_cb.setChecked(sticky)

        self.dialog.delay_cb.setChecked(bool(config.get("delay_before", False)))

        self._apply_loop_settings(config)
        self._apply_stop_after_settings(config)
        self._apply_pause_settings(config)
        self._apply_error_settings(config)
        self._apply_break_settings(config)

        typing_text = config.get("typing_text", "")
        if not isinstance(typing_text, str):
            typing_text = ""
        self.host.text_edit.setPlainText(typing_text)

        self.sync_runtime_attrs()