import json
import pyautogui
import subprocess
import win32gui
import time


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

    if not isinstance(action, dict):
        result["error"] = "Action must be a JSON object"
        return result
    if set(action) != {"action", "params"}:
        result["error"] = "Action must contain only 'action' and 'params'"
        return result
    if not isinstance(action_name, str) or action_name not in TOOL_MAP:
        result["error"] = f"Unknown action: {action_name}"
        return result

    params = action.get("params")
    if not isinstance(params, dict):
        result["error"] = "Action params must be an object"
        return result

    expected_params = ACTION_PARAMS[action_name]
    if action_name == "MOVE_MOUSE":
        if set(params) not in (set(), {"x", "y"}):
            result["error"] = "MOVE_MOUSE params must contain both x and y, or neither"
            return result
    elif set(params) != set(expected_params):
        missing = set(expected_params) - set(params)
        extra = set(params) - set(expected_params)
        if missing:
            result["error"] = f"Missing required parameter(s): {', '.join(sorted(missing))}"
        else:
            result["error"] = f"Unexpected parameter(s): {', '.join(sorted(extra))}"
        return result

    for name, value in params.items():
        expected_type = expected_params.get(name)
        if expected_type is None or not isinstance(value, expected_type) or (
            expected_type is int and isinstance(value, bool)
        ):
            result["error"] = f"Invalid parameter '{name}'"
            return result
        if expected_type is str and not value.strip():
            result["error"] = f"Parameter '{name}' must not be empty"
            return result
        if expected_type is int and value < 0:
            result["error"] = f"Parameter '{name}' must be non-negative"
            return result

    try:
        tool_result = TOOL_MAP[action_name](**params)
    except Exception as error:
        result["error"] = str(error)
        return result

    result["ok"] = True
    result["result"] = tool_result
    return result