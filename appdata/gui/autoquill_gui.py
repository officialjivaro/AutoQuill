# autoquill_gui.py
import sys
import threading
import time
import random
import pyautogui
from pynput import keyboard
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QTextEdit, QSizePolicy, QLineEdit
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from appdata.config.constants import APP_NAME, FUNCTION_KEYS, SPEEDS
from appdata.logic.typing_logic import perform_typing

class ExternalLinkPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

class AutoQuillApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(600, 700)
        self.function_key = FUNCTION_KEYS[0]
        self.speed = "Moderate"
        self.simulate_human_errors = False
        self.typing_active = False
        self.typing_thread = None
        self.default_min_interval = 15
        self.default_max_interval = 40
        self.default_min_errors = 1
        self.default_max_errors = 4
        self.init_ui()
        self.start_keyboard_listener()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        row1 = QHBoxLayout()
        fkey_label = QLabel("Activation Key:")
        self.fkey_combo = QComboBox()
        self.fkey_combo.addItems(FUNCTION_KEYS)
        self.fkey_combo.currentTextChanged.connect(self.on_fkey_changed)
        speed_label = QLabel("Typing Speed:")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(SPEEDS.keys())
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)
        row1.addWidget(fkey_label)
        row1.addWidget(self.fkey_combo)
        row1.addSpacing(20)
        row1.addWidget(speed_label)
        row1.addWidget(self.speed_combo)
        row1.setAlignment(Qt.AlignHCenter)
        main_layout.addLayout(row1)
        row2 = QHBoxLayout()
        self.error_checkbox = QCheckBox("Simulate Human Errors")
        self.error_checkbox.toggled.connect(self.on_toggled_simulate_errors)
        row2.addWidget(self.error_checkbox)
        row2.setAlignment(Qt.AlignHCenter)
        main_layout.addLayout(row2)
        row3 = QHBoxLayout()
        min_int_label = QLabel("Min Interval:")
        self.min_int_entry = QLineEdit()
        self.min_int_entry.setText(str(self.default_min_interval))
        self.min_int_entry.setFixedWidth(50)
        max_int_label = QLabel("Max Interval:")
        self.max_int_entry = QLineEdit()
        self.max_int_entry.setText(str(self.default_max_interval))
        self.max_int_entry.setFixedWidth(50)
        min_err_label = QLabel("Min Errors:")
        self.min_err_entry = QLineEdit()
        self.min_err_entry.setText(str(self.default_min_errors))
        self.min_err_entry.setFixedWidth(50)
        max_err_label = QLabel("Max Errors:")
        self.max_err_entry = QLineEdit()
        self.max_err_entry.setText(str(self.default_max_errors))
        self.max_err_entry.setFixedWidth(50)
        row3.addWidget(min_int_label)
        row3.addWidget(self.min_int_entry)
        row3.addSpacing(10)
        row3.addWidget(max_int_label)
        row3.addWidget(self.max_int_entry)
        row3.addSpacing(20)
        row3.addWidget(min_err_label)
        row3.addWidget(self.min_err_entry)
        row3.addSpacing(10)
        row3.addWidget(max_err_label)
        row3.addWidget(self.max_err_entry)
        row3.setAlignment(Qt.AlignHCenter)
        main_layout.addLayout(row3)
        row4 = QHBoxLayout()
        self.start_delay_checkbox = QCheckBox("Start Delay (2s)")
        row4.addWidget(self.start_delay_checkbox)
        row4.setAlignment(Qt.AlignHCenter)
        main_layout.addLayout(row4)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter text to type here...")
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.text_edit)
        self.embed_ad(main_layout)

    def embed_ad(self, parent_layout):
        self.ad_view = QWebEngineView()
        self.ad_view.setPage(ExternalLinkPage(self.ad_view))
        self.ad_view.setFixedHeight(70)
        ad_html = """
        <html>
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script async
              src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4223077320283786"
              crossorigin="anonymous">
            </script>
          </head>
          <body style="background-color:#323232; margin:0; padding:0; text-align:center;">
            <ins class="adsbygoogle"
                 style="display:inline-block;width:320px;height:50px"
                 data-ad-client="ca-pub-4223077320283786"
                 data-ad-slot="4075767995"></ins>
            <script>
               (adsbygoogle = window.adsbygoogle || []).push({});
            </script>
          </body>
        </html>
        """
        self.ad_view.setHtml(ad_html, QUrl("https://www.jivaro.net"))
        parent_layout.addWidget(self.ad_view)

    def on_fkey_changed(self, new_text):
        self.function_key = new_text

    def on_speed_changed(self, new_text):
        self.speed = new_text

    def on_toggled_simulate_errors(self, checked):
        self.simulate_human_errors = checked

    def start_keyboard_listener(self):
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def on_key_press(self, key):
        try:
            if hasattr(key, 'name') and key.name.lower() == self.function_key.lower():
                if not self.typing_active:
                    self.start_typing()
                else:
                    self.stop_typing()
        except Exception:
            pass

    def start_typing(self):
        self.typing_active = True
        self.typing_thread = threading.Thread(target=self.invoke_typing_logic, daemon=True)
        self.typing_thread.start()

    def stop_typing(self):
        self.typing_active = False

    def invoke_typing_logic(self):
        if self.start_delay_checkbox.isChecked():
            time.sleep(2)
        content = self.text_edit.toPlainText()
        if not content.strip():
            self.typing_active = False
            return
        delay = SPEEDS.get(self.speed, 0.05)
        try:
            min_interval = int(self.min_int_entry.text())
            max_interval = int(self.max_int_entry.text())
            min_errors = int(self.min_err_entry.text())
            max_errors = int(self.max_err_entry.text())
        except ValueError:
            min_interval = self.default_min_interval
            max_interval = self.default_max_interval
            min_errors = self.default_min_errors
            max_errors = self.default_max_errors
        perform_typing(
            content=content,
            delay=delay,
            simulate_human_errors=self.simulate_human_errors,
            min_interval=min_interval,
            max_interval=max_interval,
            min_errors=min_errors,
            max_errors=max_errors,
            is_typing_active=lambda: self.typing_active
        )
        self.stop_typing()