# File: appdata/core/constants.py
APP_NAME = "AutoQuill"
FUNCTION_KEYS = [f"F{i}" for i in range(1, 13)]

# WPM settings (single source of truth)
DEFAULT_WPM: int = 60
WPM_MIN: int = 1
WPM_MAX: int = 200


def wpm_to_delay(wpm: int) -> float:
    """
    Convert words-per-minute to an average per-character delay (seconds),
    using the standard 5 chars per word assumption.

    Clamps input to [WPM_MIN, WPM_MAX] and falls back to DEFAULT_WPM if needed.
    """
    try:
        wpm_int = int(wpm)
    except Exception:
        wpm_int = DEFAULT_WPM

    wpm_int = max(WPM_MIN, min(WPM_MAX, wpm_int))

    chars_per_min = wpm_int * 5.0
    return 60.0 / chars_per_min
