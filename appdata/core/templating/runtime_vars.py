# appdata/core/templating/runtime_vars.py
import re, datetime
from PySide6.QtGui import QGuiApplication

_TOKEN_RE = re.compile(r'\{([A-Z]+)\}')
_ESC_START = '""{'
_ESC_END = '}""'


def _now():
    return datetime.datetime.now()


def _clipboard_text() -> str:
    inst = QGuiApplication.instance()
    if inst is None:
        return ""
    return QGuiApplication.clipboard().text()


_DYNAMIC = {
    "DATE": lambda: _now().strftime("%Y-%m-%d"),
    "TIME": lambda: _now().strftime("%H:%M:%S"),
    "CLIPBOARD": _clipboard_text,
}


def expand(text: str) -> str:
    """Replace {TOKEN} placeholders unless they are wrapped by the custom
    literal‑escape  ""{TOKEN}""."""
    out = []
    i = 0
    ln = len(text)
    while i < ln:

        if text.startswith(_ESC_START, i):
            j = text.find(_ESC_END, i + 3)
            if j != -1:
                out.append(text[i + 2 : j + 3])  # keep the braces
                i = j + 3
                continue

        m = _TOKEN_RE.match(text, i)
        if m:
            key = m.group(1)
            repl = _DYNAMIC.get(key)
            if repl:
                out.append(str(repl()))
                i = m.end()
                continue

        out.append(text[i])
        i += 1
    return "".join(out)
