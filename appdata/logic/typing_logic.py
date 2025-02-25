# typing_logic.py
import time
import random
import pyautogui

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
        pyautogui.typewrite(char)
        typed_count += 1
        if simulate_human_errors:
            if typed_count >= mistake_threshold:
                for _ in range(errors_to_make):
                    random_char = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                    pyautogui.typewrite(random_char)
                    time.sleep(delay * speed_variation)
                for _ in range(errors_to_make):
                    pyautogui.press('backspace')
                    time.sleep(delay * speed_variation)
                typed_count = 0
                mistake_threshold = random.randint(min_interval, max_interval)
                errors_to_make = random.randint(min_errors, max_errors)