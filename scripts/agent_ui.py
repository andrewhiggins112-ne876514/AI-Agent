import json
import queue
import re
import threading
import tkinter as tk
from tkinter import scrolledtext
import urllib.error
import urllib.request

from tools import execute_action, parse_action_response


ANSI_ESCAPE_PATTERN = re.compile(
    r"(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~]|\x1B[@-Z\\-_]"
)


def strip_ansi_escape_sequences(text):
    return ANSI_ESCAPE_PATTERN.sub("", text)


root = tk.Tk()

root.title("AI Agent")
root.geometry("1000x800")


title = tk.Label(
    root,
    text="AI Agent",
    font=("Segoe UI", 18, "bold")
)

title.pack(pady=10)


request_label = tk.Label(
    root,
    text="Request"
)

request_label.pack()


request_entry = tk.Entry(
    root,
    width=100
)

request_entry.pack(pady=5)

status_label = tk.Label(
    root,
    text="Ready"
)

status_label.pack()


output_box = scrolledtext.ScrolledText(
    root,
    width=120,
    height=30
)

output_box.pack(pady=10)

OLLAMA_TIMEOUT_SECONDS = 120
RESULT_POLL_INTERVAL_MS = 100
result_queue = queue.Queue()
is_processing = False


def _run_ollama(request, prompt):
    try:
        api_request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({
                "model": "llama3.2",
                "prompt": prompt,
                "format": "json",
                "stream": False,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(
            api_request,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as response:
            api_result = json.loads(response.read().decode("utf-8"))
        if not isinstance(api_result, dict):
            raise ValueError("Ollama API returned an invalid response object")
        generated_response = api_result.get("response")
        if not isinstance(generated_response, str):
            raise ValueError("Ollama API response is missing a string 'response' field")
    except (TimeoutError, urllib.error.URLError) as error:
        if isinstance(error, urllib.error.URLError) and not isinstance(
            error.reason, TimeoutError
        ):
            result_queue.put((request, "failed", str(error)))
            return
        result_queue.put((request, "timeout", str(error)))
    except (OSError, ValueError) as error:
        result_queue.put((request, "failed", str(error)))
    else:
        result_queue.put((request, "completed", generated_response))


def _show_response(raw_response):
    response = strip_ansi_escape_sequences(raw_response).strip()
    output_box.insert(tk.END, "RESPONSE SOURCE:\nOLLAMA API\n\n")
    output_box.insert(tk.END, "RAW RESPONSE:\n")
    output_box.insert(tk.END, f"{raw_response.strip()}\n\n")
    output_box.insert(tk.END, "SANITISED RESPONSE:\n")
    output_box.insert(tk.END, f"{response}\n\n")

    try:
        actions = parse_action_response(response)
    except ValueError as error:
        output_box.insert(tk.END, "PARSED ACTIONS:\n")
        output_box.insert(tk.END, f"Parse error: {error}\n\n")
        output_box.insert(tk.END, "EXECUTION RESULTS:\n")
        output_box.insert(
            tk.END,
            f"{json.dumps({'ok': False, 'action': None, 'error': str(error)}, indent=2)}\n"
        )
        return False

    output_box.insert(tk.END, "PARSED ACTIONS:\n")
    output_box.insert(tk.END, f"{json.dumps(actions, indent=2)}\n\n")
    output_box.insert(tk.END, "EXECUTION RESULTS:\n")

    all_succeeded = True
    for action in actions:
        execution_result = execute_action(action)
        output_box.insert(
            tk.END,
            f"{json.dumps(execution_result, ensure_ascii=False)}\n"
        )
        if not execution_result["ok"]:
            all_succeeded = False

    return all_succeeded


def _finish_request(status, clear_request=False):
    global is_processing
    is_processing = False
    request_entry.configure(state=tk.NORMAL)
    if clear_request:
        request_entry.delete(0, tk.END)
    execute_button.configure(state=tk.NORMAL)
    status_label.configure(text=status)


def _poll_ollama_result(request):
    try:
        result_request, result_type, payload = result_queue.get_nowait()
    except queue.Empty:
        root.after(
            RESULT_POLL_INTERVAL_MS,
            _poll_ollama_result,
            request,
        )
        return

    if result_request != request:
        output_box.insert(
            tk.END,
            f"Request failed: received a result for an unexpected request.\n"
        )
        output_box.insert(tk.END, "Request failed\n")
        _finish_request("Failed")
        return

    try:
        if result_type == "timeout":
            output_box.insert(
                tk.END,
                f"Request timed out after {OLLAMA_TIMEOUT_SECONDS} seconds: {request}\n"
            )
            output_box.insert(tk.END, "Request timed out\n")
            _finish_request("Timed out")
            return

        if result_type == "failed":
            output_box.insert(tk.END, f"AI ERROR: {payload}\n")
            output_box.insert(tk.END, f"Request failed: {request}\n")
            _finish_request("Failed")
            return

        succeeded = _show_response(payload)
        if succeeded:
            output_box.insert(tk.END, f"Request completed: {request}\n")
            _finish_request("Completed", clear_request=True)
        else:
            output_box.insert(tk.END, f"Request failed: {request}\n")
            _finish_request("Failed")
    except Exception as error:
        output_box.insert(tk.END, f"Request failed: {error}\n")
        _finish_request("Failed")
        raise


def execute():
    global is_processing
    if is_processing:
        return

    request = request_entry.get().strip()
    if not request:
        return

    is_processing = True
    execute_button.configure(state=tk.DISABLED)
    request_entry.configure(state=tk.DISABLED)
    status_label.configure(text="Processing...")
    output_box.insert(tk.END, f"\nUSER: {request}\n\n")
    output_box.insert(tk.END, f"Request started: {request}\n")

    system_prompt = """
Convert the user's request into the minimum ordered list of actions needed.

Return only valid JSON using this schema:
{
  "actions": [
    {
      "action": "ACTION_NAME",
      "params": {}
    }
  ]
}

Available actions:
- OPEN_NOTEPAD: Open Notepad. Parameters: {}
- TAKE_SCREENSHOT: Capture the current desktop. Parameters: {}
- MOVE_MOUSE: Move the pointer. Parameters: {} or {"x": integer, "y": integer}
- LIST_WINDOWS: List visible windows. Parameters: {}
- TYPE_TEXT: Type the exact requested text into the active application.
  Parameters: {"text": string}

Rules:
- Include an action only if the user requested it or it is necessary to fulfill
  the request.
- Include every requested action in execution order.
- Do not invent actions or text.
- A request to take a screenshot requires TAKE_SCREENSHOT only.
- Return {"actions": []} if no available action applies.
"""
    prompt = f"{system_prompt}\n\nUser: {request}"

    try:
        worker = threading.Thread(
            target=_run_ollama,
            args=(request, prompt),
            daemon=True,
        )
        worker.start()
    except RuntimeError as error:
        output_box.insert(tk.END, f"Request failed: {error}\n")
        _finish_request("Failed")
        return

    root.after(
        RESULT_POLL_INTERVAL_MS,
        _poll_ollama_result,
        request,
    )
    output_box.see(tk.END)


def handle_request_enter(event):
    execute()
    return "break"


execute_button = tk.Button(
    root,
    text="Execute",
    command=execute,
    height=2,
    width=20
)

execute_button.pack(pady=10)


request_entry.bind("<Return>", handle_request_enter)
request_entry.bind("<KP_Enter>", handle_request_enter)


root.mainloop()
