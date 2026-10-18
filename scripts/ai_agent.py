import subprocess
import pyautogui

SYSTEM_PROMPT = """
You are an assistant controlling Windows.

Available actions:

OPEN_NOTEPAD
TAKE_SCREENSHOT

Reply with ONLY one action.
"""

while True:

    user_request = input("\nRequest: ")

    if user_request.lower() == "quit":
        break

    prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_request}"

    result = subprocess.run(
        ["ollama", "run", "llama3.2", prompt],
        capture_output=True,
        text=True
    )

    action = result.stdout.strip()

    print("\nAI Response:")
    print(action)

    if action == "OPEN_NOTEPAD":
        subprocess.Popen("notepad.exe")

    elif action == "TAKE_SCREENSHOT":
        image = pyautogui.screenshot()
        image.save(r"D:\AI-Agent\logs\screenshot.png")