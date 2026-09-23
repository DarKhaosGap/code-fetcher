import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

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

from fetch_resource import (
    Config,
    ConfigError,
    build_url,
    fetch_class_sources,
    write_sources_text,
)


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
            build_url(self.config, "com/test/Test"),
            "https://domain.com/25.6.7/com/test/Test.java",
        )

    def test_existing_java_suffix_is_not_duplicated(self):
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


class LocalSourceTests(unittest.TestCase):
    def test_uses_local_sources_then_fetches_missing_dependency_remotely(self):
        config = Config("https", "domain.com", "1.0", "user", "pass")
        with tempfile.TemporaryDirectory() as folder:
            source_root = Path(folder) / "src" / "main" / "java" / "com" / "example"
            source_root.mkdir(parents=True)
            (source_root / "Example.java").write_text(
                "import com.example.Local;\nimport com.remote.Remote;\nclass Example {}",
                encoding="utf-8",
            )
            (source_root / "Local.java").write_text("class Local {}", encoding="utf-8")

            with patch("fetch_resource.fetch_resource", return_value="class Remote {}") as fetch:
                sources = fetch_class_sources("com.example.Example", config, source_folder=folder)

        self.assertEqual(
            sources,
            [
                ("com.example.Example", "import com.example.Local;\nimport com.remote.Remote;\nclass Example {}"),
                ("com.example.Local", "class Local {}"),
                ("com.remote.Remote", "class Remote {}"),
            ],
        )
        fetch.assert_called_once_with("com/remote/Remote", config, 30.0)


class TextOutputTests(unittest.TestCase):
    def test_writes_all_sources_with_class_name_headers(self):
        sources = [
            ("com.example.Example", "class Example {}"),
            ("com.example.Dependency", "class Dependency { String value = \"olá\"; }"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "dependencies.txt"
            write_sources_text(sources, str(output_path))

            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "===== com.example.Example =====\nclass Example {}\n\n"
                "===== com.example.Dependency =====\n"
                "class Dependency { String value = \"olá\"; }",
            )


if __name__ == "__main__":
    unittest.main()
