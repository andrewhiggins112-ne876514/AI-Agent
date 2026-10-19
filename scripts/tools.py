import json
import pyautogui
import subprocess
import win32gui
import win32process
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ForegroundWindowSnapshot:
    title: str | None = None
    window_handle: int | None = None
    process_id: int | None = None
    error: str | None = None


def take_screenshot():
    image = pyautogui.screenshot()
    image.save(r"D:\AI-Agent\logs\screenshot.png")
    return "Screenshot saved"


def move_mouse(x=500, y=500):
    pyautogui.moveTo(x, y, duration=2)
    return "Mouse moved"


def open_notepad():
    subprocess.Popen("notepad.exe")
    return "Opened Notepad"


def type_text(text="Hello I am your AI Agent"):

    time.sleep(1)

    pyautogui.write(
        text,
        interval=0.05
    )

    return f"Typed: {text}"


def get_windows():

    windows = []

    def callback(hwnd, windows):

        if win32gui.IsWindowVisible(hwnd):

            title = win32gui.GetWindowText(hwnd)

            if title:
                windows.append(title)

    win32gui.EnumWindows(callback, windows)

    return windows


def get_foreground_window_snapshot():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return ForegroundWindowSnapshot()

    title = win32gui.GetWindowText(hwnd) or None
    _, process_id = win32process.GetWindowThreadProcessId(hwnd)
    return ForegroundWindowSnapshot(
        title=title,
        window_handle=int(hwnd),
        process_id=int(process_id) if process_id else None,
    )


TOOL_MAP = {
    "OPEN_NOTEPAD": open_notepad,
    "TAKE_SCREENSHOT": take_screenshot,
    "MOVE_MOUSE": move_mouse,
    "LIST_WINDOWS": get_windows,
    "TYPE_TEXT": type_text,
}

ACTION_PARAMS = {
    "OPEN_NOTEPAD": {},
    "TAKE_SCREENSHOT": {},
    "MOVE_MOUSE": {"x": int, "y": int},
    "LIST_WINDOWS": {},
    "TYPE_TEXT": {"text": str},
}


def validate_action(action):
    """Validate an action without invoking its tool."""
    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object")
    if set(action) != {"action", "params"}:
        raise ValueError("Action must contain only 'action' and 'params'")

    action_name = action["action"]
    if not isinstance(action_name, str) or action_name not in TOOL_MAP:
        raise ValueError(f"Unknown action: {action_name}")

    params = action["params"]
    if not isinstance(params, dict):
        raise ValueError("Action params must be an object")

    expected_params = ACTION_PARAMS[action_name]
    if action_name == "MOVE_MOUSE":
        if set(params) not in (set(), {"x", "y"}):
            raise ValueError("MOVE_MOUSE params must contain both x and y, or neither")
    elif set(params) != set(expected_params):
        missing = set(expected_params) - set(params)
        extra = set(params) - set(expected_params)
        if missing:
            raise ValueError(
                f"Missing required parameter(s): {', '.join(sorted(missing))}"
            )
        raise ValueError(f"Unexpected parameter(s): {', '.join(sorted(extra))}")

    for name, value in params.items():
        expected_type = expected_params.get(name)
        if expected_type is None or not isinstance(value, expected_type) or (
            expected_type is int and isinstance(value, bool)
        ):
            raise ValueError(f"Invalid parameter '{name}'")
        if expected_type is str and not value.strip():
            raise ValueError(f"Parameter '{name}' must not be empty")
        if expected_type is int and value < 0:
            raise ValueError(f"Parameter '{name}' must be non-negative")


def parse_action_response(response):
    """Parse JSON actions, retaining support for the original line-based format."""
    content = response.strip()
    if not content:
        raise ValueError("The model returned an empty response")

    if content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()
        if content.lower().startswith("json"):
            content = content[4:].strip()

    if content.startswith(("[", "{")):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON action response: {error.msg}") from error

        if isinstance(decoded, dict):
            if set(decoded) == {"actions"}:
                actions = decoded["actions"]
                if not isinstance(actions, list):
                    raise ValueError("JSON 'actions' value must be an array")
                return actions
            if set(decoded) == {"action", "params"}:
                return [decoded]
            raise ValueError(
                "JSON response must contain 'actions' or one 'action' and 'params'"
            )
        if isinstance(decoded, list):
            return decoded
        raise ValueError(
            "JSON response must be an actions object, action object, or array of actions"
        )

    actions = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("TYPE_TEXT:"):
            actions.append({
                "action": "TYPE_TEXT",
                "params": {"text": line[len("TYPE_TEXT:"):].strip()},
            })
        else:
            actions.append({"action": line, "params": {}})
    return actions


def execute_action(action):
    """Validate and execute one action, returning a structured outcome."""
    action_name = action.get("action") if isinstance(action, dict) else None
    result = {"ok": False, "action": action_name}

    try:
        validate_action(action)
    except ValueError as error:
        result["error"] = str(error)
        return result

    try:
        params = action["params"]
        tool_result = TOOL_MAP[action_name](**params)
    except Exception as error:
        result["error"] = str(error)
        return result

    result["ok"] = True
    result["result"] = tool_result
    return result