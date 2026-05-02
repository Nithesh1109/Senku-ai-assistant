# Types text using keyboard automation

import pyautogui
import time

def type_text(text: str):
    time.sleep(1)
    pyautogui.write(text, interval=0.05)
