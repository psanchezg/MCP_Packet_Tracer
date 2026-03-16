"""
Bridge singleton and HTTP helpers for PT <-> MCP communication.

Module-level state replaces the old nonlocal closure pattern.
Includes retry logic with exponential backoff, plan persistence, and undo.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from ....infrastructure.execution.live_bridge import PTCommandBridge
from ....shared.logging import get_logger

logger = get_logger(__name__)

_BRIDGE_URL = "http://127.0.0.1:54321"
_BOOTSTRAP = (
    '/* PT-MCP Bridge */ window.webview.evaluateJavaScriptAsync('
    '"setInterval(function(){var x=new XMLHttpRequest();'
    "x.open('GET','http://127.0.0.1:54321/next',true);"
    'x.onload=function(){if(x.status===200&&x.responseText)'
    "{$se('runCode',x.responseText)}};x.onerror=function(){};"
    'x.send()},500)");'
)

_bridge_instance: PTCommandBridge | None = None
_last_commands: list[str] = []
_PLAN_PERSIST_PATH = Path("projects/.last_plan.json")
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.5  # seconds


# -- low-level HTTP with retry -----------------------------------------------


def _http_request(
    url: str,
    method: str = "GET",
    body: str | None = None,
    timeout: float = 2.0,
    retries: int = 0,
) -> tuple[int | None, str | None]:
    """Execute an HTTP request with optional retries and exponential backoff."""
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            if method == "POST" and body is not None:
                data = body.encode("utf-8")
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "text/plain")
            else:
                req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8")
        except Exception:
            if attempt < attempts - 1:
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.debug(
                    "HTTP %s %s failed, retry %d/%d in %.1fs",
                    method, url, attempt + 1, retries, delay,
                )
                time.sleep(delay)
    return None, None


def http_get(url: str, timeout: float = 2.0) -> tuple[int | None, str | None]:
    """HTTP GET with no retries (backwards compatible)."""
    return _http_request(url, "GET", timeout=timeout)


def http_get_retry(url: str, timeout: float = 2.0) -> tuple[int | None, str | None]:
    """HTTP GET with retries and exponential backoff."""
    return _http_request(url, "GET", timeout=timeout, retries=_MAX_RETRIES)


def http_post(url: str, body: str, timeout: float = 3.0) -> tuple[int | None, str | None]:
    """HTTP POST with no retries (backwards compatible)."""
    return _http_request(url, "POST", body, timeout=timeout)


def http_post_retry(url: str, body: str, timeout: float = 3.0) -> tuple[int | None, str | None]:
    """HTTP POST with retries and exponential backoff."""
    return _http_request(url, "POST", body, timeout=timeout, retries=_MAX_RETRIES)


# -- bridge lifecycle ---------------------------------------------------------


def bridge_is_up() -> bool:
    """Check if the bridge HTTP server is responding."""
    status, _ = http_get(f"{_BRIDGE_URL}/ping", timeout=1.0)
    return status == 200


def bridge_pt_connected() -> bool:
    """Check if Packet Tracer is polling the bridge."""
    status, body = http_get(f"{_BRIDGE_URL}/status", timeout=1.0)
    if status == 200 and body:
        try:
            return json.loads(body).get("connected", False)
        except Exception:
            pass
    return False


def ping_bridge() -> dict:
    """Full health check of bridge and PT connectivity.

    Returns:
        Dict with bridge_up, pt_connected, and url fields.
    """
    up = bridge_is_up()
    connected = bridge_pt_connected() if up else False
    return {
        "bridge_up": up,
        "pt_connected": connected,
        "url": _BRIDGE_URL,
    }


def ensure_bridge() -> bool:
    """Start the bridge if not already running. Returns True when operational."""
    global _bridge_instance
    if bridge_is_up():
        return True
    if _bridge_instance is None:
        try:
            b = PTCommandBridge()
            b.start()
            _bridge_instance = b
            logger.info("Bridge started on %s", _BRIDGE_URL)
        except OSError:
            logger.warning("Could not start bridge — port blocked")
            return False
    return bridge_is_up()


# -- high-level helpers -------------------------------------------------------


def js_escape(s: str) -> str:
    """Escape a string for safe insertion into JS string literals."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")


def bridge_send_and_wait(js_call: str, timeout: float = 10.0) -> str | None:
    """Send a JS command via the bridge and wait for the result (with retries on POST)."""
    status_post, _ = http_post_retry(f"{_BRIDGE_URL}/queue", js_call)
    if status_post != 200:
        return None
    status_get, body = http_get(f"{_BRIDGE_URL}/result", timeout=timeout)
    if status_get == 200:
        return body
    return None


def check_bridge() -> str | None:
    """Returns an error message if the bridge isn't ready, or None if OK."""
    if not ensure_bridge():
        return "Could not start bridge on :54321."
    if not bridge_pt_connected():
        return (
            "Bridge active but PT is not connected.\n"
            "Run the bootstrap in Builder Code Editor."
        )
    return None


def get_bridge_url() -> str:
    """Return the bridge base URL."""
    return _BRIDGE_URL


def get_bootstrap() -> str:
    """Return the bootstrap JavaScript snippet."""
    return _BOOTSTRAP


# -- plan persistence ---------------------------------------------------------


def save_last_plan(plan_json: str) -> None:
    """Persist the last successful plan to disk for recovery."""
    try:
        _PLAN_PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PLAN_PERSIST_PATH.write_text(plan_json, encoding="utf-8")
        logger.debug("Saved last plan to %s", _PLAN_PERSIST_PATH)
    except OSError as e:
        logger.warning("Could not persist plan: %s", e)


def load_last_plan() -> str | None:
    """Load the last persisted plan, or None if not found."""
    if _PLAN_PERSIST_PATH.exists():
        return _PLAN_PERSIST_PATH.read_text(encoding="utf-8")
    return None


# -- undo support -------------------------------------------------------------


def record_command(cmd: str) -> None:
    """Record a command sent to PT for undo purposes."""
    _last_commands.append(cmd)
    if len(_last_commands) > 100:
        _last_commands.pop(0)


def get_last_command() -> str | None:
    """Return the last recorded command, or None."""
    return _last_commands[-1] if _last_commands else None


def pop_last_command() -> str | None:
    """Pop and return the last recorded command."""
    return _last_commands.pop() if _last_commands else None


def clear_command_history() -> None:
    """Clear all recorded commands."""
    _last_commands.clear()


def _extract_ptbuilder_calls(script: str) -> list[str]:
    """
    Parse a PTBuilder JS script into complete function calls.

    Splits only on top-level semicolons while preserving multiline
    configureDevice() calls and ignoring single-line comments outside
    string literals.
    """
    calls: list[str] = []
    current: list[str] = []
    nesting = 0
    in_string: str | None = None
    escaped = False
    in_line_comment = False
    i = 0

    while i < len(script):
        char = script[i]
        next_char = script[i + 1] if i + 1 < len(script) else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_string:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            i += 1
            continue

        if char == "/" and next_char == "/":
            in_line_comment = True
            i += 2
            continue

        if char in ('"', "'"):
            in_string = char
            current.append(char)
            i += 1
            continue

        if char in "([{":
            nesting += 1
            current.append(char)
            i += 1
            continue

        if char in ")]}":
            nesting = max(0, nesting - 1)
            current.append(char)
            i += 1
            continue

        if char == ";" and nesting == 0:
            stmt = "".join(current).strip()
            if stmt:
                calls.append(stmt)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    stmt = "".join(current).strip()
    if stmt:
        calls.append(stmt)

    return calls
