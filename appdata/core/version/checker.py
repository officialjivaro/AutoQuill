# File: appdata/core/version/checker.py
import re
from typing import Optional, Tuple

import requests

from appdata.core.version.model import VERSION
from appdata.ui.message_boxes.new_version_prompt import show_new_version_prompt
from appdata.ui.message_boxes.update_check_failed import show_update_check_failed

_VERSION_URLS = (
    "https://raw.githubusercontent.com/officialjivaro/AutoQuill/main/appdata/core/version/model.py",
    "https://raw.githubusercontent.com/officialjivaro/AutoQuill/main/appdata/version/version.py",
)

_VERSION_LINE_RE = re.compile(r'^\s*VERSION\s*=\s*["\']([^"\']+)["\']')


def check_version() -> None:
    """
    Check GitHub for a newer version of AutoQuill.
    Shows a prompt if a newer version is available; otherwise stays silent.
    """
    remote_version = None

    for url in _VERSION_URLS:
        try:
            resp = requests.get(
                url,
                timeout=5,
                headers={
                    "User-Agent": f"AutoQuill/{VERSION} (+https://jivaro.net)",
                    "Cache-Control": "no-cache",
                },
            )
        except Exception:
            continue

        if resp.status_code != 200:
            continue

        remote_version = _extract_version(resp.text)
        if remote_version:
            break

    if not remote_version:
        show_update_check_failed()
        return

    if _compare_versions(VERSION, remote_version):
        show_new_version_prompt(remote_version)


def _extract_version(text: str) -> Optional[str]:
    """
    Extract VERSION from a python source file.
    Expected format: VERSION = "0.12" (whitespace tolerant).
    """
    for line in text.splitlines():
        m = _VERSION_LINE_RE.match(line)
        if not m:
            continue
        v = m.group(1).strip()
        if v.lower().startswith("v"):
            v = v[1:].strip()
        return v or None
    return None


def _parse_version(ver: str) -> Optional[Tuple[int, ...]]:
    """
    Parse a version string like '0.12' or '0.12.1' into a tuple of ints.
    Non-numeric suffixes (e.g. '0.12-beta') are ignored.
    """
    if not isinstance(ver, str):
        return None

    s = ver.strip()
    if not s:
        return None

    if s.lower().startswith("v"):
        s = s[1:].strip()

    m = re.match(r"(\d+(?:\.\d+)*)", s)
    if not m:
        return None

    parts = m.group(1).split(".")
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except Exception:
            return None
    return tuple(out)


def _compare_versions(local_ver: str, remote_ver: str) -> bool:
    """
    Return True if remote_ver is newer than local_ver.
    """
    local_t = _parse_version(local_ver)
    remote_t = _parse_version(remote_ver)
    if not local_t or not remote_t:
        return False

    n = max(len(local_t), len(remote_t))
    local_t = local_t + (0,) * (n - len(local_t))
    remote_t = remote_t + (0,) * (n - len(remote_t))

    return remote_t > local_t
