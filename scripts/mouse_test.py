import pyautogui
import time

print("Mouse will move in 5 seconds...")
time.sleep(5)

pyautogui.moveTo(500, 500, duration=2)

print("Done")