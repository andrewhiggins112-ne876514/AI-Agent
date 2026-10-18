import win32gui

windows = []

def callback(hwnd, windows):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            windows.append(title)

win32gui.EnumWindows(callback, windows)

print("\nOpen Windows:\n")

for window in windows:
    print(window)