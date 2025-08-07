# appdata/ui/message_boxes/update_check_failed.py
from PySide6.QtWidgets import QMessageBox

def show_update_check_failed():
    msg = QMessageBox()
    msg.setWindowTitle("Update Check Failed")
    msg.setText("Unable to check for updates.\nProceeding with the current version.")
    msg.setIcon(QMessageBox.Warning)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()
