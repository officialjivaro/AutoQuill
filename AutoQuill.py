import sys
from PySide6.QtWidgets import QApplication
from appdata.gui.autoquill_gui import AutoQuillApp

if __name__ == "__main__":
    print("[INFO] Starting AutoQuill application...")
    app = QApplication(sys.argv)
    window = AutoQuillApp()
    window.show()
    app.exec()
    print("[INFO] Application closed.")
