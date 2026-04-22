# AutoQuill.py
import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from appdata.core.version.checker import check_version
from appdata.ui.windows.main_window import AutoQuillApp


APP_USER_MODEL_ID = "Jivaro.AutoQuill"


def _resource_path(*parts: str) -> Path:
    """
    Resolve a resource path for both normal source runs and PyInstaller one-file runs.
    """
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_dir.joinpath(*parts)


def _set_windows_app_user_model_id(app_id: str) -> None:
    """
    Give Windows a stable app identity so the running taskbar button can use the app icon.
    """
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        # Do not crash startup if Windows refuses the call.
        pass


def _build_app_icon() -> QIcon:
    """
    Build one QIcon from the bundled icon files if they exist.
    """
    icon = QIcon()

    for rel_parts in (
        ("appdata", "resources", "images", "icon.ico"),
        ("appdata", "resources", "images", "icon.png"),
    ):
        path = _resource_path(*rel_parts)
        if path.is_file():
            icon.addFile(str(path))

    return icon


if __name__ == "__main__":
    print("[INFO] Starting AutoQuill application...")

    _set_windows_app_user_model_id(APP_USER_MODEL_ID)

    app = QApplication(sys.argv)

    app_icon = _build_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    check_version()

    window = AutoQuillApp()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    window.show()

    exit_code = app.exec()
    print("[INFO] Application closed.")
    sys.exit(exit_code)