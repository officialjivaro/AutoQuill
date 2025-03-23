import requests
import sys
from appdata.version.version import VERSION
from appdata.message_box.update_check_failed import show_update_check_failed
from appdata.message_box.new_version_prompt import show_new_version_prompt

def check_version():
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/officialjivaro/AutoQuill/main/appdata/version/version.py",
            timeout=5
        )
        if response.status_code != 200:
            show_update_check_failed()
            return
        lines = response.text.splitlines()
        remote_version = None
        for line in lines:
            if line.startswith("VERSION"):
                remote_version = line.split("=")[1].strip().replace('"', "").replace("'", "")
                break
        if not remote_version:
            show_update_check_failed()
            return

        if _compare_versions(VERSION, remote_version):
            show_new_version_prompt(remote_version)
    except:
        show_update_check_failed()

def _compare_versions(local_ver, remote_ver):
    try:
        return float(remote_ver) > float(local_ver)
    except:
        return False
