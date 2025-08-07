# appdata/core/typing/engine.py
import time, random
from appdata.core.typing.windows_injector import inject_unicode_char, press_backspace, press_special_key
from appdata.core.templating.runtime_vars import expand
from appdata.core.typing.tokenizer import tokenise


def compile_instructions(text: str):
    """Expand runtime tokens then convert to the instruction list."""
    return tokenise(expand(text))


def perform_full_typing_loop(instructions, delay, simulate_human_errors, min_interval, max_interval, min_errors, max_errors, is_typing_active, loop_enabled, loop_min_s, loop_max_s):
    while True:
        perform_typing(instructions, delay, simulate_human_errors, min_interval, max_interval, min_errors, max_errors, is_typing_active)
        if not is_typing_active() or not loop_enabled:
            break
        for _ in range(random.randint(loop_min_s, loop_max_s)):
            if not is_typing_active():
                return
            time.sleep(1)


def _inject_random_errors(count, delay, sv):
    for _ in range(count):
        inject_unicode_char(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
        time.sleep(delay * sv)
    for _ in range(count):
        press_backspace()
        time.sleep(delay * sv)


def perform_typing(instructions, delay, simulate_human_errors, min_interval, max_interval, min_errors, max_errors, is_typing_active):
    typed = 0
    threshold = random.randint(min_interval, max_interval)
    err_cnt = random.randint(min_errors, max_errors)
    for kind, payload in instructions:
        if not is_typing_active():
            break
        sv = random.uniform(0.8, 1.2)
        time.sleep(delay * sv)
        if kind == "CHAR":
            inject_unicode_char(payload)
        else:
            press_special_key(payload)
        typed += 1
        if simulate_human_errors and typed >= threshold:
            _inject_random_errors(err_cnt, delay, sv)
            typed = 0
            threshold = random.randint(min_interval, max_interval)
            err_cnt = random.randint(min_errors, max_errors)
