# AutoQuill.py
import sys
from PySide6.QtWidgets import QApplication
from appdata.core.version.checker import check_version
from appdata.ui.main import AutoQuillApp

if __name__ == "__main__":
    print("[INFO] Starting AutoQuill application...")
    app = QApplication(sys.argv)
    check_version()
    window = AutoQuillApp()
    window.show()
    app.exec()
    print("[INFO] Application closed.")
