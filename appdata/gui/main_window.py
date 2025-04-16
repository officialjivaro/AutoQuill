import sys
import threading
import time
import random
from pynput import keyboard
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QAction
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPlainTextEdit, QSizePolicy, QLineEdit, QGroupBox,
    QMenuBar, QMenu
)

from appdata.config.constants import APP_NAME, FUNCTION_KEYS, SPEEDS
from appdata.logic.main_window import MainWindowLogic
from appdata.version.version import VERSION

class ExternalLinkPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

class AutoQuillApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setWindowIcon(QIcon("appdata/assets/images/icon.ico"))
        self.resize(500, 600)

        self.function_key = FUNCTION_KEYS[0]
        self.speed = "Moderate"
        self.simulate_human_errors = False
        self.typing_active = False
        self.typing_thread = None
        self.default_min_interval = 15
        self.default_max_interval = 40
        self.default_min_errors = 1
        self.default_max_errors = 4

        self.logic = MainWindowLogic(self)
        self.init_ui()
        self.create_menu()
        self.start_keyboard_listener()

    def create_menu(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #323232;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #454545;
            }
            QMenu {
                background-color: #323232;
                color: #ffffff;
            }
            QMenu::item:selected {
                background-color: #454545;
            }
        """)

        file_menu = menubar.addMenu("File")
        install_action = QAction("Install", self)
        install_action.triggered.connect(self.logic.install_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.logic.exit_app)
        file_menu.addAction(install_action)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Help")
        commands_action = QAction("Commands", self)
        commands_action.triggered.connect(self.logic.open_commands)
        about_action = QAction("About Jivaro", self)
        about_action.triggered.connect(self.logic.open_about_jivaro)
        discord_action = QAction("Discord", self)
        discord_action.triggered.connect(self.logic.open_discord)
        help_menu.addAction(commands_action)
        help_menu.addAction(about_action)
        help_menu.addAction(discord_action)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        typing_behavior_box = QGroupBox("Typing Behavior")
        typing_behavior_layout = QVBoxLayout(typing_behavior_box)

        row1 = QHBoxLayout()
        fkey_label = QLabel("Activation Key:")
        self.fkey_combo = QComboBox()
        self.fkey_combo.addItems(FUNCTION_KEYS)
        self.fkey_combo.currentTextChanged.connect(self.on_fkey_changed)

        speed_label = QLabel("Typing Speed:")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(SPEEDS.keys())
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)

        self.start_delay_checkbox = QCheckBox("Delay 2s before typing")

        row1.addWidget(fkey_label)
        row1.addWidget(self.fkey_combo)
        row1.addSpacing(15)
        row1.addWidget(speed_label)
        row1.addWidget(self.speed_combo)
        row1.addSpacing(15)
        row1.addWidget(self.start_delay_checkbox)
        row1.setAlignment(Qt.AlignHCenter)
        typing_behavior_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(5)
        row2.addStretch()
        self.loop_checkbox = QCheckBox("Loop Typing")
        loop_wait_label = QLabel("Wait between loops:")
        self.loop_min_label = QLabel("Min(s):")
        self.loop_min_entry = QLineEdit("5")
        self.loop_min_entry.setFixedWidth(50)
        self.loop_max_label = QLabel("Max(s):")
        self.loop_max_entry = QLineEdit("10")
        self.loop_max_entry.setFixedWidth(50)

        row2.addWidget(self.loop_checkbox)
        row2.addWidget(loop_wait_label)
        row2.addWidget(self.loop_min_label)
        row2.addWidget(self.loop_min_entry)
        row2.addWidget(self.loop_max_label)
        row2.addWidget(self.loop_max_entry)
        row2.addStretch()
        typing_behavior_layout.addLayout(row2)

        main_layout.addWidget(typing_behavior_box)

        error_settings_box = QGroupBox("Error Settings")
        error_settings_layout = QVBoxLayout(error_settings_box)

        row_err_1 = QHBoxLayout()
        row_err_1.setSpacing(5)
        row_err_1.addStretch()
        self.error_checkbox = QCheckBox("Simulate Human Errors")
        self.error_checkbox.toggled.connect(self.on_toggled_simulate_errors)
        row_err_1.addWidget(self.error_checkbox)
        row_err_1.addStretch()
        error_settings_layout.addLayout(row_err_1)

        row_err_2 = QHBoxLayout()
        row_err_2.setSpacing(10)
        row_err_2.addStretch()

        min_int_label = QLabel("Min Interval(Chars):")
        self.min_int_entry = QLineEdit(str(self.default_min_interval))
        self.min_int_entry.setFixedWidth(50)

        max_int_label = QLabel("Max Interval(Chars):")
        self.max_int_entry = QLineEdit(str(self.default_max_interval))
        self.max_int_entry.setFixedWidth(50)

        min_err_label = QLabel("Min Errors(Count):")
        self.min_err_entry = QLineEdit(str(self.default_min_errors))
        self.min_err_entry.setFixedWidth(50)

        max_err_label = QLabel("Max Errors(Count):")
        self.max_err_entry = QLineEdit(str(self.default_max_errors))
        self.max_err_entry.setFixedWidth(50)

        row_err_2.addWidget(min_int_label)
        row_err_2.addWidget(self.min_int_entry)
        row_err_2.addSpacing(10)
        row_err_2.addWidget(max_int_label)
        row_err_2.addWidget(self.max_int_entry)
        row_err_2.addSpacing(20)
        row_err_2.addWidget(min_err_label)
        row_err_2.addWidget(self.min_err_entry)
        row_err_2.addSpacing(10)
        row_err_2.addWidget(max_err_label)
        row_err_2.addWidget(self.max_err_entry)

        row_err_2.addStretch()
        error_settings_layout.addLayout(row_err_2)
        main_layout.addWidget(error_settings_box)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter text to type (plain text only)...")
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.text_edit)

        self.embed_ad(main_layout)

    def embed_ad(self, parent_layout):
        self.ad_profile = QWebEngineProfile("AdProfile", self)
        self.ad_profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/108.0.0.0 Safari/537.36"
        )

        self.ad_view = QWebEngineView(self)
        self.ad_page = ExternalLinkPage(self.ad_profile, self.ad_view)
        self.ad_view.setPage(self.ad_page)

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
                 data-ad-slot="5482552078">
            </ins>
            <script>
               (adsbygoogle = window.adsbygoogle || []).push({});
            </script>
          </body>
        </html>
        """
        self.ad_view.setHtml(ad_html, QUrl("https://jivaro.net/downloads/programs/info/jtype"))
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
        self.logic.handle_key_press(key)

    def start_typing(self):
        self.logic.start_typing()

    def stop_typing(self):
        self.logic.stop_typing()

    def invoke_typing_logic(self):
        self.logic.invoke_typing_logic()
