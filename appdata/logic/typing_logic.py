# typing_logic.py
import time
import random
import sys
import platform
from appdata.logic.windows_key_injector import inject_unicode_char, press_backspace, press_special_key, SPECIAL_KEYS

def perform_full_typing_loop(
    content,
    delay,
    simulate_human_errors,
    min_interval,
    max_interval,
    min_errors,
    max_errors,
    is_typing_active,
    loop_enabled,
    loop_min_s,
    loop_max_s
):
    while True:
        perform_typing(
            content,
            delay,
            simulate_human_errors,
            min_interval,
            max_interval,
            min_errors,
            max_errors,
            is_typing_active
        )
        if not is_typing_active():
            break
        if not loop_enabled:
            break
        loop_delay = random.randint(loop_min_s, loop_max_s)
        counter = 0
        while counter < loop_delay:
            if not is_typing_active():
                break
            time.sleep(1)
            counter += 1
        if not is_typing_active():
            break

def perform_typing(
    content,
    delay,
    simulate_human_errors,
    min_interval,
    max_interval,
    min_errors,
    max_errors,
    is_typing_active
):
    typed_count = 0
    mistake_threshold = random.randint(min_interval, max_interval)
    errors_to_make = random.randint(min_errors, max_errors)
    i = 0
    while i < len(content):
        if not is_typing_active():
            break
        speed_variation = random.uniform(0.8, 1.2)
        time.sleep(delay * speed_variation)
        ch = content[i]
        if ch == '\n' or ch == '\r':
            press_special_key("ENTER")
            typed_count += 1
            i += 1
            continue
        if i + 3 < len(content) and content.startswith('""[', i):
            end_index = content.find(']""', i+3)
            if end_index != -1:
                literal_chunk = content[i+2:end_index+1]
                for c in literal_chunk:
                    try:
                        time.sleep(delay * speed_variation)
                        inject_unicode_char(c)
                        typed_count += 1
                    except:
                        pass
                i = end_index + 3
                if simulate_human_errors and typed_count >= mistake_threshold:
                    for _ in range(errors_to_make):
                        random_char = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                        time.sleep(delay * speed_variation)
                        try:
                            inject_unicode_char(random_char)
                        except:
                            pass
                    for _ in range(errors_to_make):
                        time.sleep(delay * speed_variation)
                        try:
                            press_backspace()
                        except:
                            pass
                    typed_count = 0
                    mistake_threshold = random.randint(min_interval, max_interval)
                    errors_to_make = random.randint(min_errors, max_errors)
                continue
        if ch == '[':
            j = content.find(']', i)
            if j != -1:
                token = content[i+1:j].upper()
                if token in SPECIAL_KEYS:
                    press_special_key(token)
                    typed_count += 1
                    i = j + 1
                    if simulate_human_errors and typed_count >= mistake_threshold:
                        for _ in range(errors_to_make):
                            random_char = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                            time.sleep(delay * speed_variation)
                            try:
                                inject_unicode_char(random_char)
                            except:
                                pass
                        for _ in range(errors_to_make):
                            time.sleep(delay * speed_variation)
                            try:
                                press_backspace()
                            except:
                                pass
                        typed_count = 0
                        mistake_threshold = random.randint(min_interval, max_interval)
                        errors_to_make = random.randint(min_errors, max_errors)
                    continue
                else:
                    try:
                        inject_unicode_char(ch)
                        typed_count += 1
                    except:
                        pass
            else:
                try:
                    inject_unicode_char(ch)
                    typed_count += 1
                except:
                    pass
        else:
            try:
                inject_unicode_char(ch)
                typed_count += 1
            except:
                pass
        if simulate_human_errors and typed_count >= mistake_threshold:
            for _ in range(errors_to_make):
                random_char = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                time.sleep(delay * speed_variation)
                try:
                    inject_unicode_char(random_char)
                except:
                    pass
            for _ in range(errors_to_make):
                time.sleep(delay * speed_variation)
                try:
                    press_backspace()
                except:
                    pass
            typed_count = 0
            mistake_threshold = random.randint(min_interval, max_interval)
            errors_to_make = random.randint(min_errors, max_errors)
        i += 1
