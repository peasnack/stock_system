import logging

import requests

from config import NOTIFY_ENABLED, NOTIFY_TIMEOUT_SECONDS, WECHAT_WEBHOOK_URL

logger = logging.getLogger(__name__)


def send_wechat_message(message: str) -> bool:
    if not NOTIFY_ENABLED:
        print(f"模拟发送消息：{message}")
        logger.info("Wechat notification skipped because NOTIFY_ENABLED is false")
        return True

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

    logger.info("Wechat notification sent")
    return True


if __name__ == "__main__":
    send_wechat_message("A股投资决策系统测试消息")
