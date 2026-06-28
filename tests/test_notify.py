import unittest
from unittest.mock import patch

from notify import wechat


class LinuxWechatGuiNotifyTest(unittest.TestCase):
    def test_returns_false_when_xdotool_is_missing(self) -> None:
        with patch("notify.wechat.shutil.which", return_value=None):
            self.assertFalse(wechat._send_linux_wechat_gui_message("test"))

    def test_send_dispatches_to_linux_wechat_gui_channel(self) -> None:
        with (
            patch("notify.wechat.NOTIFY_ENABLED", True),
            patch("notify.wechat.NOTIFY_CHANNEL", "linux_wechat_gui"),
            patch("notify.wechat._send_linux_wechat_gui_message", return_value=True) as sender,
        ):
            self.assertTrue(wechat.send_wechat_message("test"))

        sender.assert_called_once_with("test")

    def test_send_rejects_unknown_channel(self) -> None:
        with (
            patch("notify.wechat.NOTIFY_ENABLED", True),
            patch("notify.wechat.NOTIFY_CHANNEL", "unknown"),
        ):
            self.assertFalse(wechat.send_wechat_message("test"))


if __name__ == "__main__":
    unittest.main()
