import os
import unittest

from core.network import akshare_network_env


class AkshareNetworkEnvTest(unittest.TestCase):
    def test_temporarily_removes_proxy_environment(self) -> None:
        original = os.environ.get("HTTP_PROXY")
        os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"

        try:
            with akshare_network_env():
                self.assertNotIn("HTTP_PROXY", os.environ)
            self.assertEqual(os.environ.get("HTTP_PROXY"), "http://127.0.0.1:7897")
        finally:
            if original is None:
                os.environ.pop("HTTP_PROXY", None)
            else:
                os.environ["HTTP_PROXY"] = original


if __name__ == "__main__":
    unittest.main()
