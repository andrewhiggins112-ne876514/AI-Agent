import pyautogui
import time

print("Open Notepad now...")
time.sleep(5)

pyautogui.write(
    "Hello. I am typing automatically.",
    interval=0.05
)

print("Done")