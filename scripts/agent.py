import pyautogui
import subprocess
import win32gui

def list_windows():
    windows = []

    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append(title)

    win32gui.EnumWindows(callback, windows)

    print("\nOpen Windows:\n")

    for window in windows:
        print("-", window)

while True:

    command = input("\nCommand: ").lower()

    if command == "notepad":
        subprocess.Popen("notepad.exe")
        print("Opened Notepad")

    elif command == "screenshot":
        image = pyautogui.screenshot()
        image.save(r"D:\AI-Agent\logs\screenshot.png")
        print("Screenshot saved")

    elif command == "mouse":
        pyautogui.moveTo(500, 500, duration=2)
        print("Mouse moved")

    elif command == "windows":
        list_windows()

    elif command == "quit":
        break

    else:
        print("Unknown command")