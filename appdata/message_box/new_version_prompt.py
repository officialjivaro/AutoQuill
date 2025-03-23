import os
import webbrowser
from PySide6.QtWidgets import QMessageBox

def show_new_version_prompt(remote_version):
    msg = QMessageBox()
    msg.setWindowTitle("New Version Available")
    msg.setText(f"A newer version ({remote_version}) is available.\nDownload now?")
    msg.setIcon(QMessageBox.Information)
    yes_button = msg.addButton("Yes", QMessageBox.AcceptRole)
    no_button = msg.addButton("No", QMessageBox.RejectRole)
    msg.exec()

    if msg.clickedButton() == yes_button:
        webbrowser.open("https://jivaro.net/downloads/programs/info/jtype")
        os._exit(0) 