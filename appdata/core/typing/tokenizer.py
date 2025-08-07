# appdata/core/typing/tokenizer.py
import re
from appdata.core.typing.windows_injector import SPECIAL_KEYS

_KEY_RE = re.compile(r'\[([A-Z0-9]+)(?:\*(\d+))?]')  # [NAME] or [NAME*NUM]
_ESC_START = '""['
_ESC_END = ']""'


def tokenise(text: str):
    """Convert expanded text into a list of ('CHAR', c) / ('KEY', name) tuples."""
    instr = []
    i = 0
    ln = len(text)
    while i < ln:

        if text.startswith(_ESC_START, i):
            j = text.find(_ESC_END, i + 3)
            if j != -1:
                for c in text[i + 2 : j + 1]:
                    instr.append(("CHAR", c))
                i = j + 3
                continue

        if text[i] == "\r" and i + 1 < ln and text[i + 1] == "\n":
            instr.append(("KEY", "ENTER"))
            i += 2
            continue

        if text[i] in ("\n", "\r"):
            instr.append(("KEY", "ENTER"))
            i += 1
            continue

        m = _KEY_RE.match(text, i)
        if m:
            name, mult = m.groups()
            if name in SPECIAL_KEYS:
                count = int(mult) if mult and mult.isdigit() else 1
                instr.extend([("KEY", name)] * count)
                i = m.end()
                continue

        instr.append(("CHAR", text[i]))
        i += 1
    return instr
