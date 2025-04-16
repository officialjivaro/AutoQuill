# /appdata/logic/main_window.py
import time
import threading
import random
import webbrowser
from pynput import keyboard
from appdata.config.constants import SPEEDS
from appdata.logic.typing_logic import perform_full_typing_loop

class MainWindowLogic:
    def __init__(self, gui):
        self.gui = gui

    def handle_key_press(self, key):
        try:
            if hasattr(key, 'name') and key.name.lower() == self.gui.function_key.lower():
                if not self.gui.typing_active:
                    self.start_typing()
                else:
                    self.stop_typing()
        except:
            pass

    def start_typing(self):
        self.gui.typing_active = True
        self.gui.typing_thread = threading.Thread(target=self.invoke_typing_logic, daemon=True)
        self.gui.typing_thread.start()

    def stop_typing(self):
        self.gui.typing_active = False

    def invoke_typing_logic(self):
        if self.gui.start_delay_checkbox.isChecked():
            time.sleep(2)

        content = self.gui.text_edit.toPlainText()
        if not content.strip():
            self.gui.typing_active = False
            return

        delay = SPEEDS.get(self.gui.speed, 0.05)
        try:
            min_interval = int(self.gui.min_int_entry.text())
            max_interval = int(self.gui.max_int_entry.text())
            min_errors = int(self.gui.min_err_entry.text())
            max_errors = int(self.gui.max_err_entry.text())
        except ValueError:
            min_interval = self.gui.default_min_interval
            max_interval = self.gui.default_max_interval
            min_errors = self.gui.default_min_errors
            max_errors = self.gui.default_max_errors

        loop_enabled = self.gui.loop_checkbox.isChecked()
        try:
            loop_min_s = int(self.gui.loop_min_entry.text())
            loop_max_s = int(self.gui.loop_max_entry.text())
        except ValueError:
            loop_min_s = 5
            loop_max_s = 10

        perform_full_typing_loop(
            content=content,
            delay=delay,
            simulate_human_errors=self.gui.simulate_human_errors,
            min_interval=min_interval,
            max_interval=max_interval,
            min_errors=min_errors,
            max_errors=max_errors,
            is_typing_active=lambda: self.gui.typing_active,
            loop_enabled=loop_enabled,
            loop_min_s=loop_min_s,
            loop_max_s=loop_max_s
        )
        self.stop_typing()

    def install_action(self):
        # No functionality yet
        pass

    def exit_app(self):
        self.gui.close()

    def open_commands(self):
        webbrowser.open("https://www.jivaro.net/downloads/programs/info/jtype")

    def open_about_jivaro(self):
        webbrowser.open("https://www.jivaro.net/")

    def open_discord(self):
        webbrowser.open("https://discord.gg/GDfX5BFGye")
