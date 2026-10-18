import pyautogui

image = pyautogui.screenshot()
image.save(r"D:\AI-Agent\logs\screenshot.png")

print("Screenshot saved")
