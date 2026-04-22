# appdata/core/typing/engine.py
import ctypes
import random
import sys
import threading
import time
from typing import Callable, Optional

from appdata.core.templating.runtime_vars import expand
from appdata.core.typing.tokenizer import tokenise
from appdata.core.typing.windows_injector import (
    inject_unicode_char,
    press_backspace,
    press_special_key,
)

# Optional import: if this fails (missing file or incompatible env),
# keep the app running by disabling breaks gracefully.
try:
    from appdata.core.typing.break_scheduler import BreakConfig, BreakScheduler  # type: ignore

    _BREAKS_AVAILABLE = True
except Exception:
    BreakScheduler = None  # type: ignore
    BreakConfig = None  # type: ignore
    _BREAKS_AVAILABLE = False


ProgressCallback = Callable[[int, int], None]

_TIMER_RESOLUTION_MS = 1
_timer_lock = threading.Lock()
_timer_refcount = 0
_timer_available = False
_winmm = None


def _init_high_res_timer() -> None:
    global _timer_available, _winmm
    if sys.platform != "win32":
        _timer_available = False
        return
    try:
        _winmm = ctypes.WinDLL("winmm")
        _winmm.timeBeginPeriod.argtypes = [ctypes.c_uint]
        _winmm.timeBeginPeriod.restype = ctypes.c_uint
        _winmm.timeEndPeriod.argtypes = [ctypes.c_uint]
        _winmm.timeEndPeriod.restype = ctypes.c_uint
        _timer_available = True
    except Exception:
        _winmm = None
        _timer_available = False


_init_high_res_timer()


def _enable_high_res_timer() -> None:
    if not _timer_available:
        return
    global _timer_refcount
    with _timer_lock:
        if _timer_refcount == 0:
            try:
                # why: higher timer resolution significantly improves short sleep accuracy on Windows.
                _winmm.timeBeginPeriod(int(_TIMER_RESOLUTION_MS))
            except Exception:
                return
        _timer_refcount += 1


def _disable_high_res_timer() -> None:
    if not _timer_available:
        return
    global _timer_refcount
    with _timer_lock:
        if _timer_refcount <= 0:
            _timer_refcount = 0
            return
        _timer_refcount -= 1
        if _timer_refcount == 0:
            try:
                _winmm.timeEndPeriod(int(_TIMER_RESOLUTION_MS))
            except Exception:
                pass


def _estimate_extra_delay_per_char(
    *,
    breaks_cfg: Optional[dict],
    simulate_pauses_cfg: Optional[dict],
) -> float:
    """
    Estimate how much extra pause time is being added per typed character.

    Why: when pauses/breaks are enabled, they can dominate the total elapsed time
    so strongly that increasing WPM barely changes the real-world speed. This
    helper gives us a simple way to compensate for that overhead.
    """
    extra_delay = 0.0

    if simulate_pauses_cfg:
        try:
            every_min = max(1, int(simulate_pauses_cfg.get("every_min_chars", 1)))
            every_max = max(1, int(simulate_pauses_cfg.get("every_max_chars", 1)))
            pause_min = max(0.0, float(simulate_pauses_cfg.get("min_seconds", 0.0)))
            pause_max = max(0.0, float(simulate_pauses_cfg.get("max_seconds", 0.0)))

            avg_chars_between_pauses = (every_min + every_max) / 2.0
            avg_pause_seconds = (pause_min + pause_max) / 2.0

            extra_delay += avg_pause_seconds / avg_chars_between_pauses
        except Exception:
            pass

    if _BREAKS_AVAILABLE and breaks_cfg and bool(breaks_cfg.get("enabled")):
        try:
            word_min = max(1, int(breaks_cfg.get("word_min", 1)))
            word_max = max(1, int(breaks_cfg.get("word_max", 1)))
            sec_min = max(0.0, float(breaks_cfg.get("sec_min", 0.0)))
            sec_max = max(0.0, float(breaks_cfg.get("sec_max", 0.0)))

            avg_words_between_breaks = (word_min + word_max) / 2.0
            avg_break_seconds = (sec_min + sec_max) / 2.0

            # Standard assumption: 1 word ≈ 5 characters.
            avg_chars_between_breaks = max(1.0, avg_words_between_breaks * 5.0)

            extra_delay += avg_break_seconds / avg_chars_between_breaks
        except Exception:
            pass

    return extra_delay


def _compensated_delay(
    base_delay: float,
    *,
    breaks_cfg: Optional[dict],
    simulate_pauses_cfg: Optional[dict],
) -> float:
    """
    Adjust the base per-character delay so optional pauses/breaks do not completely
    drown out the user's chosen WPM.

    Note: if the configured pauses are extremely aggressive, no compensation can
    perfectly preserve the target speed. In that case we clamp to a small floor.
    """
    try:
        base = float(base_delay)
    except Exception:
        return float(base_delay)

    extra_delay = _estimate_extra_delay_per_char(
        breaks_cfg=breaks_cfg,
        simulate_pauses_cfg=simulate_pauses_cfg,
    )

    if extra_delay <= 0.0:
        return base

    # Keep a small floor so the app stays stable and does not try to type
    # unrealistically fast when the configured pause overhead is very large.
    return max(0.005, base - extra_delay)


def compile_instructions(text: str):
    """Expand runtime tokens then convert to the instruction list."""
    return tokenise(expand(text))


def _is_paused(is_typing_paused) -> bool:
    if is_typing_paused is None:
        return False
    try:
        return bool(is_typing_paused())
    except Exception:
        return False


def _stop_after_reached(timing: dict, stop_after_s: Optional[float]) -> bool:
    if stop_after_s is None:
        return False
    try:
        limit = float(stop_after_s)
    except Exception:
        return False
    if limit <= 0.0:
        return False

    now = time.monotonic()
    paused_total = float(timing.get("paused_total", 0.0))
    paused_since = timing.get("paused_since")
    if paused_since is not None:
        # why: don't count the current paused segment as active typing time.
        paused_total += now - float(paused_since)

    active_elapsed = now - float(timing.get("started_at", now)) - paused_total
    return active_elapsed >= limit


def _wait_while_paused(
    is_typing_active,
    is_typing_paused,
    timing: dict,
    *,
    stop_after_s: Optional[float],
    tick: float = 0.05,
) -> bool:
    """
    Block while paused, but still exit quickly if stopped.
    Updates timing["paused_total"] and timing["paused_since"] to keep active-time calculations accurate.
    """
    while _is_paused(is_typing_paused):
        if not is_typing_active():
            return False
        # Stop-after uses active time only; no need to check it here while paused.

        now = time.monotonic()
        if timing.get("paused_since") is None:
            timing["paused_since"] = now
        time.sleep(tick)

    # Transition: paused -> running
    if timing.get("paused_since") is not None:
        now = time.monotonic()
        timing["paused_total"] = float(timing.get("paused_total", 0.0)) + (
            now - float(timing["paused_since"])
        )
        timing["paused_since"] = None

    if _stop_after_reached(timing, stop_after_s):
        return False

    return True


def _sleep_with_controls(
    seconds: float,
    is_typing_active,
    is_typing_paused,
    timing: dict,
    *,
    stop_after_s: Optional[float],
    tick: float = 0.05,
) -> bool:
    """
    Sleep in small increments so we can:
      - Abort quickly on stop,
      - Pause/resume mid-sleep,
      - Honor stop-after using active typing time.
    """
    remaining = float(seconds)
    if remaining <= 0.0:
        return True

    # why: sleeping slightly under and then yielding/spinning reduces oversleep drift on some Windows setups.
    slack_max = 0.005

    while remaining > 0.0:
        if not is_typing_active():
            return False

        if not _wait_while_paused(
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
            tick=tick,
        ):
            return False

        if _stop_after_reached(timing, stop_after_s):
            return False

        slice_target = tick if remaining > tick else remaining
        slack = slack_max if slice_target > slack_max else (slice_target / 2.0)

        start = time.monotonic()
        sleep_for = slice_target - slack
        if sleep_for > 0.0:
            time.sleep(sleep_for)

        # Finish the slice without a second short sleep (which can overshoot badly on Windows).
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= slice_target:
                break
            if not is_typing_active():
                return False
            if _is_paused(is_typing_paused):
                # note: pause will be handled on the next outer-iteration boundary.
                break
            time.sleep(0)

        elapsed = time.monotonic() - start
        if elapsed <= 0.0:
            elapsed = slice_target
        remaining -= float(elapsed)

    return True


def perform_full_typing_loop(
    instructions,
    delay: float,
    simulate_human_errors: bool,
    min_interval: int,
    max_interval: int,
    min_errors: int,
    max_errors: int,
    is_typing_active,
    loop_enabled: bool,
    loop_min_s: int,
    loop_max_s: int,
    *,
    breaks_cfg=None,  # optional: {"enabled": bool, "word_min": int, "word_max": int, "sec_min": float, "sec_max": float}
    is_typing_paused=None,
    progress_cb: Optional[ProgressCallback] = None,
    stop_after_s: Optional[float] = None,
    startup_delay: float = 0.0,
    simulate_pauses_cfg: Optional[dict] = None,
):
    """
    Type the given instruction list once; if loop_enabled, wait and repeat.

    New controls:
      - Pause/Resume via is_typing_paused
      - Auto-stop after stop_after_s (active typing time only; pauses are excluded)
      - Progress reporting via progress_cb(typed_chars, total_chars)
      - Simulated pauses via simulate_pauses_cfg
    """
    _enable_high_res_timer()
    try:
        total_chars = sum(1 for kind, _ in instructions if kind == "CHAR")
        typed_chars = 0

        timing = {
            "started_at": time.monotonic(),
            "paused_total": 0.0,
            "paused_since": None,
        }

        if progress_cb is not None:
            try:
                progress_cb(typed_chars, total_chars)
            except Exception:
                pass

        # Startup delay (pause-aware so hotkey pause works immediately).
        if startup_delay and startup_delay > 0.0:
            if not _sleep_with_controls(
                float(startup_delay),
                is_typing_active,
                is_typing_paused,
                timing,
                stop_after_s=stop_after_s,
            ):
                return

        scheduler = None
        if breaks_cfg and _BREAKS_AVAILABLE and bool(breaks_cfg.get("enabled")):
            cfg = BreakConfig(
                enabled=True,
                word_min=int(breaks_cfg.get("word_min", 18)),
                word_max=int(breaks_cfg.get("word_max", 42)),
                sec_min=float(breaks_cfg.get("sec_min", 2.0)),
                sec_max=float(breaks_cfg.get("sec_max", 5.0)),
            )
            cfg.sanitize()
            scheduler = BreakScheduler(cfg)

        effective_delay = _compensated_delay(
            delay,
            breaks_cfg=breaks_cfg if scheduler is not None else None,
            simulate_pauses_cfg=simulate_pauses_cfg,
        )

        while True:
            typed_chars = perform_typing(
                instructions,
                effective_delay,
                simulate_human_errors,
                min_interval,
                max_interval,
                min_errors,
                max_errors,
                is_typing_active,
                is_typing_paused=is_typing_paused,
                progress_cb=progress_cb,
                stop_after_s=stop_after_s,
                timing=timing,
                scheduler=scheduler,
                total_chars=total_chars,
                simulate_pauses_cfg=simulate_pauses_cfg,
            )

            if (
                not is_typing_active()
                or _stop_after_reached(timing, stop_after_s)
                or not loop_enabled
            ):
                break

            # "Loop wins": treat the loop wait as if a break occurred and reset counters.
            if scheduler is not None:
                scheduler.reset_after_loop()

            # Wait between loops with early-abort checks and pause support.
            wait_s = random.randint(int(loop_min_s), int(loop_max_s))
            if wait_s < 0:
                wait_s = 0

            if wait_s:
                if not _sleep_with_controls(
                    float(wait_s),
                    is_typing_active,
                    is_typing_paused,
                    timing,
                    stop_after_s=stop_after_s,
                ):
                    return

            # Reset per-loop progress so the UI reads like "this pass through the text".
            typed_chars = 0
            if progress_cb is not None:
                try:
                    progress_cb(typed_chars, total_chars)
                except Exception:
                    pass
    finally:
        _disable_high_res_timer()


def _inject_random_errors(
    count: int,
    delay: float,
    sv: float,
    scheduler: Optional[object],
    is_typing_active,
    *,
    is_typing_paused=None,
    stop_after_s: Optional[float] = None,
    timing: Optional[dict] = None,
):
    """
    Inject random typo chars then delete them with BACKSPACE.
    This does NOT advance typed_chars progress, since it's intentionally "mistyped" output.
    """
    if timing is None:
        timing = {"started_at": time.monotonic(), "paused_total": 0.0, "paused_since": None}

    # Type random characters
    for _ in range(int(count)):
        if not is_typing_active():
            return

        if not _wait_while_paused(
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
        ):
            return

        if _stop_after_reached(timing, stop_after_s):
            return

        ch = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        inject_unicode_char(ch)

        # Advance scheduler with a CHAR token; pause if due.
        if scheduler is not None:
            pause = scheduler.step("CHAR", ch)  # type: ignore[attr-defined]
            if pause is not None:
                if not _sleep_with_controls(
                    float(pause),
                    is_typing_active,
                    is_typing_paused,
                    timing,
                    stop_after_s=stop_after_s,
                ):
                    return

        if not _sleep_with_controls(
            float(delay * sv),
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
        ):
            return

    # Delete them with BACKSPACE
    for _ in range(int(count)):
        if not is_typing_active():
            return

        if not _wait_while_paused(
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
        ):
            return

        if _stop_after_reached(timing, stop_after_s):
            return

        press_backspace()

        if scheduler is not None:
            pause = scheduler.step("KEY", "BACKSPACE")  # type: ignore[attr-defined]
            if pause is not None:
                if not _sleep_with_controls(
                    float(pause),
                    is_typing_active,
                    is_typing_paused,
                    timing,
                    stop_after_s=stop_after_s,
                ):
                    return

        if not _sleep_with_controls(
            float(delay * sv),
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
        ):
            return


def perform_typing(
    instructions,
    delay: float,
    simulate_human_errors: bool,
    min_interval: int,
    max_interval: int,
    min_errors: int,
    max_errors: int,
    is_typing_active,
    *,
    is_typing_paused=None,
    progress_cb: Optional[ProgressCallback] = None,
    stop_after_s: Optional[float] = None,
    timing: Optional[dict] = None,
    scheduler: Optional[object] = None,  # 3.9-safe; real type is BreakScheduler
    total_chars: int = 0,
    simulate_pauses_cfg: Optional[dict] = None,
) -> int:
    """
    Core typing loop. Types all tokens in 'instructions'.

    Returns:
      typed_chars: number of intended CHAR tokens typed (excludes injected error chars)
    """
    if timing is None:
        timing = {"started_at": time.monotonic(), "paused_total": 0.0, "paused_since": None}

    typed_tokens = 0
    typed_chars = 0

    threshold = (
        random.randint(int(min_interval), int(max_interval))
        if int(max_interval) >= int(min_interval)
        else int(min_interval)
    )
    err_cnt = (
        random.randint(int(min_errors), int(max_errors))
        if int(max_errors) >= int(min_errors)
        else int(min_errors)
    )

    sim_pause_enabled = False
    every_min = 0
    every_max = 0
    pause_min_s = 0.0
    pause_max_s = 0.0

    if simulate_pauses_cfg:
        try:
            every_min = int(simulate_pauses_cfg.get("every_min_chars", 0))
            every_max = int(simulate_pauses_cfg.get("every_max_chars", 0))
            pause_min_s = float(simulate_pauses_cfg.get("min_seconds", 0.0))
            pause_max_s = float(simulate_pauses_cfg.get("max_seconds", 0.0))
            if every_min < 1:
                every_min = 1
            if every_max < 1:
                every_max = 1
            if every_min > every_max:
                every_min, every_max = every_max, every_min
            if pause_min_s < 0.0:
                pause_min_s = 0.0
            if pause_max_s < 0.0:
                pause_max_s = 0.0
            if pause_min_s > pause_max_s:
                pause_min_s, pause_max_s = pause_max_s, pause_min_s
            sim_pause_enabled = True
        except Exception:
            sim_pause_enabled = False

    chars_since_pause = 0
    next_pause_at = random.randint(every_min, every_max) if sim_pause_enabled else 0

    for kind, payload in instructions:
        if not is_typing_active():
            break

        if not _wait_while_paused(
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
        ):
            break

        if _stop_after_reached(timing, stop_after_s):
            break

        sv = random.uniform(0.8, 1.2)
        if not _sleep_with_controls(
            float(delay * sv),
            is_typing_active,
            is_typing_paused,
            timing,
            stop_after_s=stop_after_s,
        ):
            break

        # Inject token into the active/attached window
        if kind == "CHAR":
            inject_unicode_char(payload)
            typed_chars += 1
            if progress_cb is not None:
                try:
                    progress_cb(typed_chars, int(total_chars))
                except Exception:
                    pass

            if sim_pause_enabled:
                chars_since_pause += 1
                if chars_since_pause >= next_pause_at:
                    pause_for = random.uniform(float(pause_min_s), float(pause_max_s))
                    if pause_for > 0.0:
                        if not _sleep_with_controls(
                            pause_for,
                            is_typing_active,
                            is_typing_paused,
                            timing,
                            stop_after_s=stop_after_s,
                        ):
                            break
                    chars_since_pause = 0
                    next_pause_at = random.randint(every_min, every_max)

        else:
            # Treat any non-CHAR as a special key
            press_special_key(payload)

        # Human-like pause scheduling (after completing a word / boundary)
        if scheduler is not None:
            pause = scheduler.step(kind, payload)  # type: ignore[attr-defined]
            if pause is not None:
                if not _sleep_with_controls(
                    float(pause),
                    is_typing_active,
                    is_typing_paused,
                    timing,
                    stop_after_s=stop_after_s,
                ):
                    break

        # Error simulation pacing (threshold in tokens to keep behavior consistent)
        typed_tokens += 1
        if simulate_human_errors and typed_tokens >= threshold:
            _inject_random_errors(
                err_cnt,
                delay,
                sv,
                scheduler,
                is_typing_active,
                is_typing_paused=is_typing_paused,
                stop_after_s=stop_after_s,
                timing=timing,
            )
            typed_tokens = 0
            threshold = (
                random.randint(int(min_interval), int(max_interval))
                if int(max_interval) >= int(min_interval)
                else int(min_interval)
            )
            err_cnt = (
                random.randint(int(min_errors), int(max_errors))
                if int(max_errors) >= int(min_errors)
                else int(min_errors)
            )

        if _stop_after_reached(timing, stop_after_s):
            break

    return typed_chars