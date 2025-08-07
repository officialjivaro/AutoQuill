# appdata/core/typing/windows_injector.py
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
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT_UNION)]

SPECIAL_KEYS = {
    "ENTER": 0x0D, "TAB": 0x09, "BACKSPACE": 0x08, "SPACE": 0x20, "SPACEBAR": 0x20,
    "ESC": 0x1B, "ESCAPE": 0x1B, "CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12,
    "CAPSLOCK": 0x14, "NUMLOCK": 0x90, "SCROLLLOCK": 0x91, "PAUSE": 0x13,
    "INS": 0x2D, "INSERT": 0x2D, "DEL": 0x2E, "DELETE": 0x2E,
    "PRTSC": 0x2C, "PRINTSCREEN": 0x2C, "HOME": 0x24, "END": 0x23,
    "PAGEUP": 0x21, "PAGEDOWN": 0x22, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "LWIN": 0x5B, "RWIN": 0x5C, "APPS": 0x5D,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
    "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "NUM0": 0x60, "NUM1": 0x61, "NUM2": 0x62, "NUM3": 0x63, "NUM4": 0x64,
    "NUM5": 0x65, "NUM6": 0x66, "NUM7": 0x67, "NUM8": 0x68, "NUM9": 0x69,
    "NUMMULTIPLY": 0x6A, "NUMADD": 0x6B, "NUMSUB": 0x6D, "NUMDECIMAL": 0x6E, "NUMDIVIDE": 0x6F,
}

EXTENDED_KEYS = {0x2D, 0x2E, 0x2C, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x5B, 0x5C, 0x5D, 0x6A, 0x6B, 0x6D, 0x6E, 0x6F}

def inject_unicode_char(ch):
    code = ord(ch)
    kd = INPUT()
    kd.type = INPUT_KEYBOARD
    kd.ki.wScan = code
    kd.ki.dwFlags = KEYEVENTF_UNICODE
    ku = INPUT()
    ku.type = INPUT_KEYBOARD
    ku.ki.wScan = code
    ku.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    arr = (INPUT * 2)(kd, ku)
    if user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT)) != 2:
        raise ctypes.WinError(ctypes.get_last_error())

def press_backspace():
    press_special_key("BACKSPACE")

def press_special_key(name):
    vk = SPECIAL_KEYS.get(name.upper())
    if not vk:
        return
    ext = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0
    kd = INPUT()
    kd.type = INPUT_KEYBOARD
    kd.ki.wVk = vk
    kd.ki.dwFlags = ext
    ku = INPUT()
    ku.type = INPUT_KEYBOARD
    ku.ki.wVk = vk
    ku.ki.dwFlags = KEYEVENTF_KEYUP | ext
    arr = (INPUT * 2)(kd, ku)
    if user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT)) != 2:
        raise ctypes.WinError(ctypes.get_last_error())
