import logging
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


def _activate_wechat_window() -> bool:
    if not shutil.which("xdotool"):
        logger.error("Linux WeChat GUI notification requires xdotool")
        return False

    search_commands = [
        ["search", "--onlyvisible", "--class", "wechat"],
        ["search", "--onlyvisible", "--name", "微信"],
        ["search", "--onlyvisible", "--name", "WeChat"],
    ]
    for command in search_commands:
        result = subprocess.run(["xdotool", *command], capture_output=True, text=True, check=False)
        window_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not window_ids:
            continue
        _run_xdotool("windowactivate", "--sync", window_ids[-1])
        time.sleep(0.5)
        return True

    logger.error("Linux WeChat GUI notification could not find a visible WeChat window")
    return False


def _send_linux_wechat_gui_message(message: str, target: str = LINUX_WECHAT_TARGET) -> bool:
    if not _activate_wechat_window():
        return False

    try:
        _run_xdotool("key", "ctrl+f")
        time.sleep(0.3)
        if not _set_clipboard(target):
            return False
        _run_xdotool("key", "ctrl+v")
        time.sleep(0.5)
        _run_xdotool("key", "Return")
        time.sleep(0.8)
        if not _set_clipboard(message):
            return False
        _run_xdotool("key", "ctrl+v")
        time.sleep(0.3)
        _run_xdotool("key", "Return")
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
