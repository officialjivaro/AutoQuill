# appdata/core/controllers/main_window_controller.py
import threading
import time
import webbrowser

# why: your project has used more than one constants path during refactoring,
# so this keeps the file paste-safe for the current state of the app.
try:
    from appdata.core.configs.constants import wpm_to_delay
except Exception:
    from appdata.core.constants import wpm_to_delay

from appdata.core.persistence import saves
from appdata.core.typing.engine import compile_instructions, perform_full_typing_loop
from appdata.core.typing.windows_injector import (
    attach_to_foreground_focus,
    detach_target,
    get_attached_target,
    is_target_valid,
)


class MainWindowLogic:
    def __init__(self, gui):
        self.gui = gui

    def handle_key_press(self, key):
        try:
            name = getattr(key, "name", None)
            if not name:
                return

            k = name.lower()

            if k == "esc":
                if self.gui.typing_active_evt.is_set():
                    self.stop_typing()
                return

            if k != self.gui.function_key_lower:
                return

            if not self.gui.typing_active_evt.is_set():
                self.start_typing()
                return

            self.toggle_pause()
        except Exception:
            # Swallow unexpected pynput quirks without crashing the app.
            pass

    def toggle_pause(self):
        if not self.gui.typing_active_evt.is_set():
            return

        if self.gui.typing_paused_evt.is_set():
            self.resume_typing()
        else:
            self.pause_typing()

    def pause_typing(self):
        if not self.gui.typing_active_evt.is_set():
            return

        self.gui.typing_paused_evt.set()
        self._set_run_status("Paused")

        with self.gui.run_lock:
            if self.gui.run_started_at > 0.0 and self.gui.run_paused_since is None:
                self.gui.run_paused_since = time.monotonic()

    def resume_typing(self):
        if not self.gui.typing_active_evt.is_set():
            return

        self.gui.typing_paused_evt.clear()
        self._set_run_status("Typing")

        now = time.monotonic()
        with self.gui.run_lock:
            if self.gui.run_paused_since is not None:
                self.gui.run_paused_total += now - self.gui.run_paused_since
                self.gui.run_paused_since = None

    def start_typing(self):
        if self.gui.typing_thread and self.gui.typing_thread.is_alive():
            return

        self.gui.typing_paused_evt.clear()

        settings = self.gui.settings_dialog.get_runtime_settings()
        sticky_enabled = bool(settings.get("sticky_typing", False))

        if sticky_enabled:
            try:
                attach_to_foreground_focus()
            except Exception:
                detach_target()
                sticky_enabled = False
        else:
            detach_target()

        snapshot = self._build_snapshot(settings)
        if not snapshot:
            detach_target()
            return

        snapshot["sticky_typing"] = sticky_enabled

        total_chars = sum(1 for kind, _ in snapshot["instructions"] if kind == "CHAR")
        self._reset_run_state(total_chars)

        self.gui.typing_active_evt.set()
        self.gui.typing_thread = threading.Thread(
            target=self._typing_worker, args=(snapshot,), daemon=True
        )
        self.gui.typing_thread.start()

    def stop_typing(self):
        # Always detach any target so subsequent runs re-capture a fresh handle.
        detach_target()
        self.gui.typing_active_evt.clear()
        self.gui.typing_paused_evt.clear()

        now = time.monotonic()
        with self.gui.run_lock:
            if self.gui.run_paused_since is not None:
                self.gui.run_paused_total += now - self.gui.run_paused_since
                self.gui.run_paused_since = None
            self.gui.run_ended_at = now

        self._set_run_status("Idle")

    def reset_typing(self) -> None:
        """Stop any current typing run and reset progress/ETA state back to the idle baseline."""
        self.stop_typing()

        now = time.monotonic()
        with self.gui.run_lock:
            self.gui.run_status = "Idle"
            self.gui.run_typed_chars = 0
            self.gui.run_total_chars = 0
            self.gui.run_started_at = 0.0
            self.gui.run_paused_total = 0.0
            self.gui.run_paused_since = None
            self.gui.run_ended_at = now

    def _reset_run_state(self, total_chars: int):
        with self.gui.run_lock:
            self.gui.run_status = "Typing"
            self.gui.run_typed_chars = 0
            self.gui.run_total_chars = int(total_chars)
            self.gui.run_started_at = time.monotonic()
            self.gui.run_paused_total = 0.0
            self.gui.run_paused_since = None
            self.gui.run_ended_at = None

    def _set_run_status(self, status: str):
        with self.gui.run_lock:
            self.gui.run_status = status

    def _typing_worker(self, cfg):
        def is_active():
            if not self.gui.typing_active_evt.is_set():
                return False
            if cfg.get("sticky_typing"):
                return is_target_valid()
            return True

        def is_paused():
            return self.gui.typing_paused_evt.is_set()

        def progress_cb(typed_chars: int, total_chars: int):
            if not self.gui.typing_active_evt.is_set():
                return

            now = time.monotonic()
            with self.gui.run_lock:
                self.gui.run_typed_chars = int(typed_chars)
                self.gui.run_total_chars = int(total_chars)

                if int(typed_chars) == 0:
                    self.gui.run_started_at = now
                    self.gui.run_paused_total = 0.0
                    self.gui.run_paused_since = None
                    self.gui.run_ended_at = None

        stop_after_s = None
        if cfg.get("stop_after_enabled"):
            stop_after_s = float(cfg.get("stop_after_seconds", 0) or 0)

        sim_pause_cfg = None
        if cfg.get("sim_pauses_enabled"):
            sim_pause_cfg = {
                "every_min_chars": int(cfg.get("pause_every_min_chars", 1)),
                "every_max_chars": int(cfg.get("pause_every_max_chars", 1)),
                "min_seconds": float(cfg.get("pause_min_seconds", 0.0)),
                "max_seconds": float(cfg.get("pause_max_seconds", 0.0)),
            }

        breaks_cfg = None
        if cfg.get("breaks_enabled"):
            breaks_cfg = {
                "enabled": True,
                "word_min": int(cfg.get("breaks_word_min", 18)),
                "word_max": int(cfg.get("breaks_word_max", 42)),
                "sec_min": float(cfg.get("breaks_sec_min", 2.0)),
                "sec_max": float(cfg.get("breaks_sec_max", 5.0)),
            }

        perform_full_typing_loop(
            instructions=cfg["instructions"],
            delay=cfg["delay"],
            simulate_human_errors=cfg["simulate_errors"],
            min_interval=cfg["min_int"],
            max_interval=cfg["max_int"],
            min_errors=cfg["min_err"],
            max_errors=cfg["max_err"],
            is_typing_active=is_active,
            is_typing_paused=is_paused,
            progress_cb=progress_cb,
            stop_after_s=stop_after_s,
            startup_delay=float(cfg.get("startup_delay", 0) or 0.0),
            simulate_pauses_cfg=sim_pause_cfg,
            breaks_cfg=breaks_cfg,
            loop_enabled=cfg["loop_enabled"],
            loop_min_s=cfg["loop_min"],
            loop_max_s=cfg["loop_max"],
        )

        self.stop_typing()
        self.gui.typing_thread = None

    def _build_snapshot(self, settings=None):
        text = self.gui.text_edit.toPlainText()
        if not text.strip():
            return None

        if settings is None:
            settings = self.gui.settings_dialog.get_runtime_settings()

        delay = wpm_to_delay(settings["wpm"])

        return {
            "instructions": compile_instructions(text),
            "delay": delay,
            "simulate_errors": settings["simulate_human_errors"],
            "min_int": settings["min_interval"],
            "max_int": settings["max_interval"],
            "min_err": settings["min_errors"],
            "max_err": settings["max_errors"],
            "loop_enabled": settings["loop_enabled"],
            "loop_min": settings["loop_min"],
            "loop_max": settings["loop_max"],
            "startup_delay": 2 if settings["delay_before"] else 0,
            "breaks_enabled": settings["breaks_enabled"],
            "breaks_word_min": settings["breaks_word_min"],
            "breaks_word_max": settings["breaks_word_max"],
            "breaks_sec_min": settings["breaks_sec_min"],
            "breaks_sec_max": settings["breaks_sec_max"],
            "stop_after_enabled": settings["stop_after_enabled"],
            "stop_after_seconds": settings["stop_after_seconds"],
            "sim_pauses_enabled": settings["simulate_pauses_enabled"],
            "pause_every_min_chars": settings["pause_every_min_chars"],
            "pause_every_max_chars": settings["pause_every_max_chars"],
            "pause_min_seconds": settings["pause_min_seconds"],
            "pause_max_seconds": settings["pause_max_seconds"],
        }

    def get_target_status(self) -> dict:
        """
        Return a small display-ready sticky-target status for the main window header.
        """
        try:
            sticky_enabled = bool(
                self.gui.settings_dialog.get_runtime_settings().get("sticky_typing", False)
            )
        except Exception:
            sticky_enabled = False

        if not sticky_enabled:
            return {
                "text": "Sticky target: Off",
                "level": "muted",
            }

        attached_target = get_attached_target()
        typing_active = self.gui.typing_active_evt.is_set()

        if attached_target is None:
            if typing_active:
                return {
                    "text": "Sticky target: No target captured",
                    "level": "warn",
                }
            return {
                "text": "Sticky target: Will capture at start",
                "level": "muted",
            }

        if is_target_valid():
            return {
                "text": "Sticky target: Locked to captured field"
                if typing_active
                else "Sticky target: Captured target ready",
                "level": "ok",
            }

        return {
            "text": "Sticky target: Captured target lost",
            "level": "warn",
        }

    def list_save_files(self):
        return saves.list_saves()

    def save_config(self, name: str):
        name = name.strip()
        if not name:
            return False

        cfg = self.gui.settings_dialog.collect_config(self.gui.text_edit.toPlainText())
        saves.save_config(cfg, name)
        return True

    def load_config(self, name: str):
        cfg = saves.load_config(name.strip())
        if not cfg:
            return False

        self._apply_config(cfg)
        return True

    def _apply_config(self, cfg: dict):
        self.gui.settings_dialog.apply_config(cfg)

        if not self.gui.settings_dialog.get_runtime_settings().get("sticky_typing", False):
            detach_target()

    # Optional hook for UI; keeps previous callsites safe.
    def invoke_typing_logic(self):
        pass

    # Menu actions (unchanged)
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

    def open_donate(self):
        webbrowser.open("https://jivaro.net/about/donate")