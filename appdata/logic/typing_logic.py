import time
import random
import sys
import platform

from appdata.logic.windows_key_injector import inject_unicode_char, press_backspace

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

    for char in content:
        if not is_typing_active():
            break

        speed_variation = random.uniform(0.8, 1.2)

        time.sleep(delay * speed_variation)

        try:
            inject_unicode_char(char)
        except:
            pass

        typed_count += 1

        if simulate_human_errors:
            if typed_count >= mistake_threshold:
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
