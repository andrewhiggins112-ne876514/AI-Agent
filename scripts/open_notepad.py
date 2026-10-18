import subprocess
import time
import pyautogui

print("Opening Notepad...")

subprocess.Popen("notepad.exe")

time.sleep(2)

pyautogui.write(
    "This note was created automatically.",
    interval=0.05
)

print("Done")