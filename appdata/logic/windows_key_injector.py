import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.LPARAM),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.LPARAM),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
            ("hi", HARDWAREINPUT),
        ]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT_UNION),
    ]

def inject_unicode_char(ch: str):
    code = ord(ch)

    keydown = INPUT()
    keydown.type = INPUT_KEYBOARD
    keydown.ki.wScan = code
    keydown.ki.dwFlags = KEYEVENTF_UNICODE
    keydown.ki.wVk = 0
    keydown.ki.time = 0
    keydown.ki.dwExtraInfo = 0

    keyup = INPUT()
    keyup.type = INPUT_KEYBOARD
    keyup.ki.wScan = code
    keyup.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    keyup.ki.wVk = 0
    keyup.ki.time = 0
    keyup.ki.dwExtraInfo = 0

    arr = (INPUT * 2)(keydown, keyup)
    n_sent = user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))
    if n_sent != 2:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput failed to inject character")

def press_backspace():

    backspace_vk = 0x08

    down = INPUT()
    down.type = INPUT_KEYBOARD
    down.ki.wVk = backspace_vk
    down.ki.wScan = 0
    down.ki.dwFlags = 0
    down.ki.time = 0
    down.ki.dwExtraInfo = 0

    up = INPUT()
    up.type = INPUT_KEYBOARD
    up.ki.wVk = backspace_vk
    up.ki.wScan = 0
    up.ki.dwFlags = KEYEVENTF_KEYUP
    up.ki.time = 0
    up.ki.dwExtraInfo = 0

    arr = (INPUT * 2)(down, up)
    n_sent = user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))
    if n_sent != 2:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput failed for backspace")