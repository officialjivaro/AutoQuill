# appdata/core/main_window.py
import time, threading, webbrowser
from appdata.core.constants import SPEEDS
from appdata.core.typing.engine import compile_instructions, perform_full_typing_loop
from appdata.core.persistence import saves


class MainWindowLogic:
    def __init__(self, gui):
        self.gui = gui

    def handle_key_press(self, key):
        try:
            if hasattr(key, "name") and key.name.lower() == self.gui.function_key_lower:
                if not self.gui.typing_active_evt.is_set():
                    self.start_typing()
                else:
                    self.stop_typing()
        except Exception:
            pass

    def start_typing(self):
        if self.gui.typing_thread and self.gui.typing_thread.is_alive():
            return
        snapshot = self._build_snapshot()
        if not snapshot:
            return
        self.gui.typing_active_evt.set()
        self.gui.typing_thread = threading.Thread(target=self._typing_worker, args=(snapshot,), daemon=True)
        self.gui.typing_thread.start()

    def stop_typing(self):
        self.gui.typing_active_evt.clear()

    def _build_snapshot(self):
        text = self.gui.text_edit.toPlainText()
        if not text.strip():
            return None
        try:
            min_i = int(self.gui.mi_e.text())
            max_i = int(self.gui.ma_e.text())
            min_e = int(self.gui.me_e.text())
            max_e = int(self.gui.mx_e.text())
        except ValueError:
            min_i = self.gui.default_min_interval
            max_i = self.gui.default_max_interval
            min_e = self.gui.default_min_errors
            max_e = self.gui.default_max_errors
        try:
            loop_min = int(self.gui.min_e.text())
            loop_max = int(self.gui.max_e.text())
        except ValueError:
            loop_min, loop_max = 5, 10
        return {
            "instructions": compile_instructions(text),
            "delay": SPEEDS.get(self.gui.speed, 0.05),
            "simulate_errors": self.gui.simulate_human_errors,
            "min_int": min_i,
            "max_int": max_i,
            "min_err": min_e,
            "max_err": max_e,
            "loop_enabled": self.gui.loop_cb.isChecked(),
            "loop_min": loop_min,
            "loop_max": loop_max,
            "startup_delay": 2 if self.gui.delay_cb.isChecked() else 0,
        }

    def _typing_worker(self, cfg):
        if cfg["startup_delay"]:
            time.sleep(cfg["startup_delay"])
            if not self.gui.typing_active_evt.is_set():
                return
        perform_full_typing_loop(
            instructions=cfg["instructions"],
            delay=cfg["delay"],
            simulate_human_errors=cfg["simulate_errors"],
            min_interval=cfg["min_int"],
            max_interval=cfg["max_int"],
            min_errors=cfg["min_err"],
            max_errors=cfg["max_err"],
            is_typing_active=lambda: self.gui.typing_active_evt.is_set(),
            loop_enabled=cfg["loop_enabled"],
            loop_min_s=cfg["loop_min"],
            loop_max_s=cfg["loop_max"],
        )
        self.stop_typing()
        self.gui.typing_thread = None

    def list_save_files(self):
        return saves.list_saves()

    def save_config(self, name: str):
        name = name.strip()
        if not name:
            return False
        saves.save_config(self._collect_gui_config(), name)
        return True

    def load_config(self, name: str):
        cfg = saves.load_config(name.strip())
        if not cfg:
            return False
        self._apply_config(cfg)
        return True

    def _collect_gui_config(self):
        try:
            loop_min = int(self.gui.min_e.text())
            loop_max = int(self.gui.max_e.text())
        except ValueError:
            loop_min, loop_max = 5, 10
        try:
            min_i = int(self.gui.mi_e.text())
            max_i = int(self.gui.ma_e.text())
            min_e = int(self.gui.me_e.text())
            max_e = int(self.gui.mx_e.text())
        except ValueError:
            min_i = self.gui.default_min_interval
            max_i = self.gui.default_max_interval
            min_e = self.gui.default_min_errors
            max_e = self.gui.default_max_errors
        return {
            "function_key": self.gui.function_key,
            "typing_speed": self.gui.speed,
            "delay_before": self.gui.delay_cb.isChecked(),
            "loop_enabled": self.gui.loop_cb.isChecked(),
            "loop_min": loop_min,
            "loop_max": loop_max,
            "simulate_human_errors": self.gui.simulate_human_errors,
            "min_interval": min_i,
            "max_interval": max_i,
            "min_errors": min_e,
            "max_errors": max_e,
            "typing_text": self.gui.text_edit.toPlainText(),
        }

    def _apply_config(self, cfg: dict):
        self.gui.fk.setCurrentText(cfg.get("function_key", self.gui.function_key))
        self.gui.sp.setCurrentText(cfg.get("typing_speed", self.gui.speed))
        self.gui.delay_cb.setChecked(bool(cfg.get("delay_before", False)))
        self.gui.loop_cb.setChecked(bool(cfg.get("loop_enabled", False)))
        self.gui.min_e.setText(str(cfg.get("loop_min", 5)))
        self.gui.max_e.setText(str(cfg.get("loop_max", 10)))
        self.gui.err_cb.setChecked(bool(cfg.get("simulate_human_errors", False)))
        self.gui.mi_e.setText(str(cfg.get("min_interval", self.gui.default_min_interval)))
        self.gui.ma_e.setText(str(cfg.get("max_interval", self.gui.default_max_interval)))
        self.gui.me_e.setText(str(cfg.get("min_errors", self.gui.default_min_errors)))
        self.gui.mx_e.setText(str(cfg.get("max_errors", self.gui.default_max_errors)))
        self.gui.text_edit.setPlainText(cfg.get("typing_text", ""))
        self.gui.function_key_lower = self.gui.function_key.lower()

    def install_action(self):
        pass

    def exit_app(self):
        self.gui.close()

    def open_commands(self):
        webbrowser.open("https://www.jivaro.net/downloads/programs/info/jtype")

    def open_proxies(self):
        webbrowser.open("https://jivaro.net/content/blog/the-best-affordable-proxy-providers")

    def open_about_jivaro(self):
        webbrowser.open("https://www.jivaro.net/")

    def open_discord(self):
        webbrowser.open("https://discord.gg/GDfX5BFGye")
