# windows_key_injector.py
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

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

SPECIAL_KEYS = {
    "ENTER": 0x0D,
    "TAB": 0x09,
    "BACKSPACE": 0x08,
    "DEL": 0x2E,
    "CAPSLOCK": 0x14,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "ALT": 0x12,
    "ESC": 0x1B,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22
}

def inject_unicode_char(ch):
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
        raise ctypes.WinError(ctypes.get_last_error())

def press_backspace():
    press_special_key("BACKSPACE")

def press_special_key(key_name):
    vk = SPECIAL_KEYS.get(key_name.upper())
    if not vk:
        return
    down = INPUT()
    down.type = INPUT_KEYBOARD
    down.ki.wVk = vk
    down.ki.wScan = 0
    down.ki.dwFlags = 0
    down.ki.time = 0
    down.ki.dwExtraInfo = 0

    up = INPUT()
    up.type = INPUT_KEYBOARD
    up.ki.wVk = vk
    up.ki.wScan = 0
    up.ki.dwFlags = KEYEVENTF_KEYUP
    up.ki.time = 0
    up.ki.dwExtraInfo = 0

    arr = (INPUT * 2)(down, up)
    n_sent = user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))
    if n_sent != 2:
        raise ctypes.WinError(ctypes.get_last_error())
