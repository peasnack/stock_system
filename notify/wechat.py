import logging

logger = logging.getLogger(__name__)


def send_wechat_message(message: str) -> bool:
    print(f"发送消息：{message}")
    logger.info("Wechat mock message sent")
    return True


if __name__ == "__main__":
    send_wechat_message("A股投资决策系统测试消息")
