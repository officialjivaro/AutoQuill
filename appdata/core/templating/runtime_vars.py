# appdata/core/templating/runtime_vars.py
import datetime
import re

from PySide6.QtGui import QGuiApplication


_TOKEN_RE = re.compile(r"\{([A-Z]+)\}")
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

# why: the main-window token helper should read from one source of truth
# instead of hard-coding token names and descriptions in the UI.
_SUPPORTED_TOKENS = (
    {
        "token": "{CLIPBOARD}",
        "description": "Insert the current clipboard text when typing starts.",
    },
    {
        "token": "{DATE}",
        "description": "Insert today's date when typing starts.",
    },
    {
        "token": "{TIME}",
        "description": "Insert the current time when typing starts.",
    },
)


def get_supported_tokens() -> list[dict[str, str]]:
    """
    Return display-ready metadata for the supported runtime tokens.

    A copy is returned so UI code does not accidentally mutate the shared source.
    """
    return [dict(item) for item in _SUPPORTED_TOKENS]


def expand(text: str) -> str:
    """Replace {TOKEN} placeholders unless they are wrapped by the custom
    literal-escape  ""{TOKEN}""."""
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