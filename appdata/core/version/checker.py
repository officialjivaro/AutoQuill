# appdata/core/version/checker.py
import requests, sys
from appdata.core.version.model import VERSION
from appdata.ui.message_boxes.update_check_failed import show_update_check_failed
from appdata.ui.message_boxes.new_version_prompt import show_new_version_prompt

def check_version():
    try:
        resp = requests.get(
            "https://raw.githubusercontent.com/officialjivaro/AutoQuill/main/appdata/version/version.py",
            timeout=5,
        )
        if resp.status_code != 200:
            show_update_check_failed()
            return
        remote_version = _extract_version(resp.text)
        if not remote_version:
            show_update_check_failed()
            return
        if _compare_versions(VERSION, remote_version):
            show_new_version_prompt(remote_version)
    except Exception:
        show_update_check_failed()

def _extract_version(text):
    for line in text.splitlines():
        if line.startswith("VERSION"):
            return line.split("=")[1].strip().replace('"', "").replace("'", "")
    return None

def _compare_versions(local_ver, remote_ver):
    try:
        return float(remote_ver) > float(local_ver)
    except Exception:
        return False
