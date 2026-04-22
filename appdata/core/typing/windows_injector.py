# File: appdata/core/typing/windows_injector.py
import ctypes
from ctypes import wintypes

# --- user32/kernel32 setup ---
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# SendInput constants (foreground fallback when no target is attached)
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

# Window message constants (background path when a target is attached)
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_UNICHAR = 0x0109
UNICODE_NOCHAR = 0xFFFF

MAPVK_VK_TO_VSC = 0

# Prototypes for Win32 APIs used via ctypes
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.GetFocus.argtypes = []
user32.GetFocus.restype = wintypes.HWND

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

# --- INPUT structures for SendInput fallback ---
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


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT_UNION)]


LPINPUT = ctypes.POINTER(INPUT)
user32.SendInput.argtypes = (wintypes.UINT, LPINPUT, ctypes.c_int)
user32.SendInput.restype = wintypes.UINT

# VK map for special keys (used by both paths)
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

# Keys that require the "extended" bit
EXTENDED_KEYS = {
    0x2D, 0x2E, 0x2C, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28,
    0x5B, 0x5C, 0x5D, 0x6A, 0x6B, 0x6D, 0x6E, 0x6F
}

# -----------------------
# Target attach/detach API
# -----------------------
_ATTACHED_HWND = wintypes.HWND(0)  # when set, all injections go to this window via PostMessageW


def attach_target(hwnd: int) -> bool:
    """Attach a target HWND; subsequent injections go to this window."""
    global _ATTACHED_HWND
    h = wintypes.HWND(hwnd)
    if user32.IsWindow(h):
        _ATTACHED_HWND = h
        return True
    _ATTACHED_HWND = wintypes.HWND(0)
    return False


def detach_target() -> None:
    """Detach any target HWND; revert to global SendInput path."""
    global _ATTACHED_HWND
    _ATTACHED_HWND = wintypes.HWND(0)


def get_attached_target() -> int | None:
    """Return the attached HWND value or None."""
    v = _ATTACHED_HWND.value
    return int(v) if v else None


def _valid_target() -> wintypes.HWND | None:
    h = _ATTACHED_HWND
    if h and user32.IsWindow(h):
        return h
    return None


def is_target_valid() -> bool:
    """
    True if either (a) no target is attached, or (b) an attached target is still a valid window.
    Use this to stop typing when a previously attached target disappears.
    """
    if _ATTACHED_HWND.value == 0:
        return True
    return bool(user32.IsWindow(_ATTACHED_HWND))


def attach_to_foreground_focus() -> int | None:
    """
    Capture the *currently focused control* of the foreground window and attach to it.
    If no child has focus, attach to the foreground window itself.
    Returns the attached HWND (int) or None on failure.
    """
    hwnd_fg = user32.GetForegroundWindow()
    if not hwnd_fg:
        return None

    pid = wintypes.DWORD(0)
    fg_tid = user32.GetWindowThreadProcessId(hwnd_fg, ctypes.byref(pid))
    cur_tid = kernel32.GetCurrentThreadId()

    if fg_tid:
        user32.AttachThreadInput(cur_tid, fg_tid, True)
    try:
        hwnd_focus = user32.GetFocus()
    finally:
        if fg_tid:
            user32.AttachThreadInput(cur_tid, fg_tid, False)

    target = hwnd_focus or hwnd_fg
    if attach_target(int(target)):
        return int(target)
    return None

# -----------------------
# Background injection helpers (PostMessageW)
# -----------------------
def _post_char(hwnd: wintypes.HWND, ch: str) -> bool:
    """Post WM_CHAR/WM_UNICHAR to a background window (no focus required)."""
    code = ord(ch)
    if code <= 0xFFFF:
        # lParam low word = repeat count (1)
        return bool(user32.PostMessageW(hwnd, WM_CHAR, code, 1))
    # Astral plane fallback
    return bool(user32.PostMessageW(hwnd, WM_UNICHAR, code, 1))


def _post_key(hwnd: wintypes.HWND, vk: int, is_down: bool) -> bool:
    """Post WM_KEYDOWN/WM_KEYUP with a well‑formed lParam (scan code + flags)."""
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC) & 0xFF
    extended = 1 if vk in EXTENDED_KEYS else 0
    repeat = 1
    lparam = (repeat & 0xFFFF) | (scan << 16) | (extended << 24)
    if not is_down:
        # Previous state + transition bits for KEYUP
        lparam |= (1 << 30) | (1 << 31)
    msg = WM_KEYDOWN if is_down else WM_KEYUP
    return bool(user32.PostMessageW(hwnd, msg, vk, lparam))

# -----------------------
# SendInput fallback helpers (foreground)
# -----------------------
def _sendinput_unicode(ch: str) -> None:
    """Foreground unicode char via SendInput (active window)."""
    code = ord(ch)
    kd = INPUT()
    kd.type = INPUT_KEYBOARD
    kd._input.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0)
    ku = INPUT()
    ku.type = INPUT_KEYBOARD
    ku._input.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)
    arr = (INPUT * 2)(kd, ku)
    if user32.SendInput(2, arr, ctypes.sizeof(INPUT)) != 2:
        raise ctypes.WinError(ctypes.get_last_error())


def _sendinput_vk(vk: int) -> None:
    """Foreground special key via SendInput (active window)."""
    ext = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0
    kd = INPUT()
    kd.type = INPUT_KEYBOARD
    kd._input.ki = KEYBDINPUT(vk, 0, ext, 0, 0)
    ku = INPUT()
    ku.type = INPUT_KEYBOARD
    ku._input.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP | ext, 0, 0)
    arr = (INPUT * 2)(kd, ku)
    if user32.SendInput(2, arr, ctypes.sizeof(INPUT)) != 2:
        raise ctypes.WinError(ctypes.get_last_error())

# -----------------------
# Public API used by the typing engine
# -----------------------
def inject_unicode_char(ch: str) -> None:
    """
    If a valid target HWND is attached, send the character via WM_CHAR to that window
    (works while unfocused). Otherwise, fall back to SendInput (active window).
    """
    hwnd = _valid_target()
    if hwnd:
        if not _post_char(hwnd, ch):
            # If PostMessage fails, do not silently redirect to another window when a target is attached.
            # We intentionally drop back to foreground only when no target is attached.
            return
        return
    _sendinput_unicode(ch)


def press_backspace() -> None:
    press_special_key("BACKSPACE")


def press_special_key(name: str) -> None:
    """
    Send a virtual-key special key either to the attached window (background)
    or via SendInput (foreground) when no target is attached.
    """
    vk = SPECIAL_KEYS.get(name.upper())
    if not vk:
        return
    hwnd = _valid_target()
    if hwnd:
        _post_key(hwnd, vk, True)
        _post_key(hwnd, vk, False)
    else:
        _sendinput_vk(vk)
