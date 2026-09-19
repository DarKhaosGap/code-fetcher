import sys
import types
import unittest

try:
    import requests  # noqa: F401
except ModuleNotFoundError:
    requests_stub = types.ModuleType("requests")
    requests_stub.RequestException = Exception
    requests_stub.HTTPError = Exception
    auth_stub = types.ModuleType("requests.auth")
    auth_stub.HTTPBasicAuth = object
    requests_stub.auth = auth_stub
    sys.modules["requests"] = requests_stub
    sys.modules["requests.auth"] = auth_stub

from fetch_resource import Config, ConfigError, build_url


class BuildUrlTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(
            protocol="https",
            domain="domain.com",
            version="25.6.7",
            username="user",
            password="pass",
        )

    def test_plain_domain_preserves_existing_url_shape(self):
        self.assertEqual(
            build_url(self.config, "com/test/Test.java"),
            "https://domain.com/25.6.7/com/test/Test.java",
        )

    def test_domain_base_path_precedes_version_and_resource(self):
        config = self.config.__class__(**{**self.config.__dict__, "domain": "domain.com/other"})
        self.assertEqual(
            build_url(config, "com/test/Test.java"),
            "https://domain.com/other/25.6.7/com/test/Test.java",
        )

    def test_trailing_domain_slash_is_normalized(self):
        config = self.config.__class__(**{**self.config.__dict__, "domain": "domain.com/other/"})
        self.assertEqual(
            build_url(config, "com/test/Test.java"),
            "https://domain.com/other/25.6.7/com/test/Test.java",
        )

    def test_rejects_unsafe_domain_values(self):
        for domain in (
            "user:pass@domain.com/other",
            "domain.com/other?query=value",
            "domain.com/other#fragment",
            "domain.com//other",
            "domain.com/../other",
            "domain.com/%2e%2e/other",
            "domain.com/other/..",
            "domain.com\\other",
            "https://domain.com/other",
        ):
            with self.subTest(domain=domain), self.assertRaises(ConfigError):
                build_url(self.config.__class__(**{**self.config.__dict__, "domain": domain}), "com/test/Test.java")


if __name__ == "__main__":
    unittest.main()
