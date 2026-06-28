import logging
import re
import shutil
import subprocess
import time

import requests

from config import (
    LINUX_WECHAT_TARGET,
    NOTIFY_CHANNEL,
    NOTIFY_ENABLED,
    NOTIFY_TIMEOUT_SECONDS,
    WECHAT_WEBHOOK_URL,
)

logger = logging.getLogger(__name__)


def _set_clipboard(text: str) -> bool:
    if shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
        return True
    if shutil.which("xsel"):
        subprocess.run(["xsel", "--clipboard", "--input"], input=text, text=True, check=True)
        return True
    if shutil.which("wl-copy"):
        subprocess.run(["wl-copy"], input=text, text=True, check=True)
        return True
    logger.error("Linux WeChat GUI notification requires xclip, xsel, or wl-copy")
    return False


def _run_xdotool(*args: str) -> None:
    subprocess.run(["xdotool", *args], check=True)


def _window_area(window_id: str) -> int:
    result = subprocess.run(
        ["xdotool", "getwindowgeometry", window_id],
        capture_output=True,
        text=True,
        check=True,
    )
    matched = re.search(r"Geometry:\s+(\d+)x(\d+)", result.stdout)
    if not matched:
        return 0
    width, height = (int(value) for value in matched.groups())
    return width * height


def _click_window_ratio(window_id: str, x_ratio: float, y_ratio: float) -> None:
    result = subprocess.run(
        ["xdotool", "getwindowgeometry", window_id],
        capture_output=True,
        text=True,
        check=True,
    )
    matched = re.search(r"Geometry:\s+(\d+)x(\d+)", result.stdout)
    if not matched:
        raise subprocess.CalledProcessError(1, ["xdotool", "getwindowgeometry", window_id])
    width, height = (int(value) for value in matched.groups())
    _run_xdotool("mousemove", "--window", window_id, str(round(width * x_ratio)), str(round(height * y_ratio)))
    _run_xdotool("click", "1")


def _search_wechat_windows() -> list[str]:
    candidates: list[str] = []
    for search_args in (
        ("search", "--onlyvisible", "--name", "^微信$"),
        ("search", "--onlyvisible", "--class", "wechat"),
    ):
        result = subprocess.run(
            ["xdotool", *search_args],
            capture_output=True,
            text=True,
            check=False,
        )
        candidates.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    return list(dict.fromkeys(candidates))


def _activate_wechat_window() -> bool:
    if not shutil.which("xdotool"):
        logger.error("Linux WeChat GUI notification requires xdotool")
        return False

    window_ids = _search_wechat_windows()
    if window_ids:
        window_id = max(window_ids, key=_window_area)
        _run_xdotool("windowraise", window_id)
        subprocess.run(["xdotool", "windowfocus", window_id], check=False)
        time.sleep(0.5)
        active_window = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True,
            text=True,
            check=False,
        )
        if active_window.stdout.strip() == window_id:
            return True
        logger.error("Linux WeChat GUI notification could not focus WeChat window")
        return False

    logger.error("Linux WeChat GUI notification could not find a visible WeChat window")
    return False


def _active_wechat_window_id() -> str | None:
    window_ids = _search_wechat_windows()
    if not window_ids:
        return None
    return max(window_ids, key=_window_area)


def _send_linux_wechat_gui_message(message: str, target: str = LINUX_WECHAT_TARGET) -> bool:
    if not _activate_wechat_window():
        return False

    try:
        window_id = _active_wechat_window_id()
        if window_id is None:
            logger.error("Linux WeChat GUI notification could not resolve active WeChat window")
            return False

        _click_window_ratio(window_id, 0.092, 0.059)
        time.sleep(0.3)
        if not _set_clipboard(target):
            return False
        _run_xdotool("key", "ctrl+a")
        _run_xdotool("key", "ctrl+v")
        time.sleep(0.8)

        _run_xdotool("key", "Return")
        time.sleep(1.0)

        _click_window_ratio(window_id, 0.092, 0.059)
        _run_xdotool("key", "ctrl+a")
        _run_xdotool("key", "BackSpace")
        time.sleep(0.8)
        _run_xdotool("key", "Return")
        time.sleep(1.0)

        if not _set_clipboard(message):
            return False
        _click_window_ratio(window_id, 0.531, 0.915)
        time.sleep(0.2)
        _run_xdotool("key", "ctrl+v")
        time.sleep(0.5)
        _click_window_ratio(window_id, 0.940, 0.965)
        time.sleep(0.5)
        _run_xdotool("key", "Return")
        time.sleep(0.2)
        _run_xdotool("key", "ctrl+Return")
    except subprocess.CalledProcessError as exc:
        logger.exception("Linux WeChat GUI notification failed: %s", exc)
        return False

    logger.info("Linux WeChat GUI notification sent to %s", target)
    return True


def _send_webhook_message(message: str) -> bool:
    if not WECHAT_WEBHOOK_URL:
        logger.error("Wechat notification enabled but WECHAT_WEBHOOK_URL is empty")
        return False

    try:
        response = requests.post(
            WECHAT_WEBHOOK_URL,
            json={"msgtype": "text", "text": {"content": message}},
            timeout=NOTIFY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Wechat notification failed: %s", exc)
        return False

    logger.info("Wechat webhook notification sent")
    return True


def send_wechat_message(message: str) -> bool:
    if not NOTIFY_ENABLED:
        print(f"模拟发送消息：{message}")
        logger.info("Wechat notification skipped because NOTIFY_ENABLED is false")
        return True

    if NOTIFY_CHANNEL == "mock":
        print(f"模拟发送消息：{message}")
        logger.info("Wechat notification channel is mock")
        return True
    if NOTIFY_CHANNEL == "webhook":
        return _send_webhook_message(message)
    if NOTIFY_CHANNEL == "linux_wechat_gui":
        return _send_linux_wechat_gui_message(message)

    logger.error("Unsupported notification channel: %s", NOTIFY_CHANNEL)
    return False


if __name__ == "__main__":
    send_wechat_message("A股投资决策系统测试消息")
