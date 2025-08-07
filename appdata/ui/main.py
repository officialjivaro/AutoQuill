# appdata/ui/main.py
import threading
from pynput import keyboard
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPlainTextEdit, QLineEdit, QGroupBox, QMenuBar, QPushButton,
    QMessageBox
)
from appdata.core.constants import APP_NAME, FUNCTION_KEYS, SPEEDS
from appdata.core.main_window import MainWindowLogic
from appdata.core.ads.adsense import create_adsense_view, load_adsense_content
from appdata.core.version.model import VERSION


class AutoQuillApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setWindowIcon(QIcon("appdata/resources/images/icon.ico"))
        self.resize(500, 600)
        self.function_key = FUNCTION_KEYS[0]
        self.function_key_lower = self.function_key.lower()
        self.speed = "Moderate"
        self.simulate_human_errors = False
        self.typing_active_evt = threading.Event()
        self.typing_thread = None
        self.default_min_interval = 15
        self.default_max_interval = 40
        self.default_min_errors = 1
        self.default_max_errors = 4
        self.logic = MainWindowLogic(self)
        self.init_ui()
        self.create_menu()
        self.start_keyboard_listener()
        self.refresh_save_list()

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

        tb = QGroupBox("Typing Behavior")
        tb_lay = QVBoxLayout(tb)
        r1 = QHBoxLayout()
        fk_lab = QLabel("Activation Key:")
        self.fk = QComboBox()
        self.fk.addItems(FUNCTION_KEYS)
        self.fk.currentTextChanged.connect(self.on_fkey_changed)
        sp_lab = QLabel("Typing Speed:")
        self.sp = QComboBox()
        self.sp.addItems(SPEEDS.keys())
        self.sp.currentTextChanged.connect(self.on_speed_changed)
        self.delay_cb = QCheckBox("Delay 2s before typing")
        r1.addWidget(fk_lab)
        r1.addWidget(self.fk)
        r1.addSpacing(15)
        r1.addWidget(sp_lab)
        r1.addWidget(self.sp)
        r1.addSpacing(15)
        r1.addWidget(self.delay_cb)
        r1.setAlignment(Qt.AlignHCenter)
        tb_lay.addLayout(r1)
        r2 = QHBoxLayout()
        r2.setSpacing(5)
        r2.addStretch()
        self.loop_cb = QCheckBox("Loop Typing")
        wait_lab = QLabel("Wait between loops:")
        min_lab = QLabel("Min(s):")
        self.min_e = QLineEdit("5")
        self.min_e.setFixedWidth(50)
        max_lab = QLabel("Max(s):")
        self.max_e = QLineEdit("10")
        self.max_e.setFixedWidth(50)
        r2.addWidget(self.loop_cb)
        r2.addWidget(wait_lab)
        r2.addWidget(min_lab)
        r2.addWidget(self.min_e)
        r2.addWidget(max_lab)
        r2.addWidget(self.max_e)
        r2.addStretch()
        tb_lay.addLayout(r2)
        lay.addWidget(tb)

        err_box = QGroupBox("Error Settings")
        err_lay = QVBoxLayout(err_box)
        e1 = QHBoxLayout()
        e1.setSpacing(5)
        e1.addStretch()
        self.err_cb = QCheckBox("Simulate Human Errors")
        self.err_cb.toggled.connect(self.on_toggled_simulate_errors)
        e1.addWidget(self.err_cb)
        e1.addStretch()
        err_lay.addLayout(e1)
        e2 = QHBoxLayout()
        e2.setSpacing(10)
        e2.addStretch()
        mi_lab = QLabel("Min Interval(Chars):")
        self.mi_e = QLineEdit(str(self.default_min_interval))
        self.mi_e.setFixedWidth(50)
        ma_lab = QLabel("Max Interval(Chars):")
        self.ma_e = QLineEdit(str(self.default_max_interval))
        self.ma_e.setFixedWidth(50)
        me_lab = QLabel("Min Errors(Count):")
        self.me_e = QLineEdit(str(self.default_min_errors))
        self.me_e.setFixedWidth(50)
        mx_lab = QLabel("Max Errors(Count):")
        self.mx_e = QLineEdit(str(self.default_max_errors))
        self.mx_e.setFixedWidth(50)
        e2.addWidget(mi_lab)
        e2.addWidget(self.mi_e)
        e2.addSpacing(10)
        e2.addWidget(ma_lab)
        e2.addWidget(self.ma_e)
        e2.addSpacing(20)
        e2.addWidget(me_lab)
        e2.addWidget(self.me_e)
        e2.addSpacing(10)
        e2.addWidget(mx_lab)
        e2.addWidget(self.mx_e)
        e2.addStretch()
        err_lay.addLayout(e2)
        lay.addWidget(err_box)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter text to type (plain text only)...")
        lay.addWidget(self.text_edit)

        save_row = QHBoxLayout()
        save_row.setAlignment(Qt.AlignHCenter)
        self.save_name_e = QLineEdit()
        self.save_name_e.setPlaceholderText("Save name")
        self.save_name_e.setFixedWidth(150)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.saves_combo = QComboBox()
        self.saves_combo.setMinimumWidth(150)
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self.on_load_clicked)
        save_row.addWidget(self.save_name_e)
        save_row.addWidget(self.save_btn)
        save_row.addSpacing(20)
        save_row.addWidget(self.saves_combo)
        save_row.addWidget(self.load_btn)
        lay.addLayout(save_row)

        self.ad_view = create_adsense_view()
        lay.addWidget(self.ad_view, alignment=Qt.AlignHCenter)
        load_adsense_content(self.ad_view)

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

    def on_speed_changed(self, t):
        self.speed = t

    def on_toggled_simulate_errors(self, c):
        self.simulate_human_errors = c

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
