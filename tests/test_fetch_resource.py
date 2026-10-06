import io
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
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
    main,
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

    def test_depth_limits_breadth_first_traversal_and_deduplicates_cycles(self):
        config = Config("https", "domain.com", "1.0", "user", "pass")
        bodies = {
            "com/example/Root": "import com.example.Left;\nimport com.example.Right;",
            "com/example/Left": "import com.example.Shared;",
            "com/example/Right": "import com.example.Shared;\nimport com.example.Tail;",
            "com/example/Shared": "import com.example.Root;\nimport com.example.Deep;",
            "com/example/Tail": "import com.example.Deep;",
            "com/example/Deep": "import com.example.Beyond;",
            "com/example/Beyond": "class Beyond {}",
        }
        cases = (
            (None, ["Root", "Left", "Right"]),
            (2, ["Root", "Left", "Right", "Shared", "Tail"]),
            (3, ["Root", "Left", "Right", "Shared", "Tail", "Deep"]),
        )
        def remote_source(path, config, timeout):
            return bodies[path]

        for depth, expected_names in cases:
            with self.subTest(depth=depth), patch("fetch_resource.fetch_resource", side_effect=remote_source) as fetch:
                if depth is None:
                    sources = fetch_class_sources("com.example.Root", config)
                else:
                    sources = fetch_class_sources("com.example.Root", config, depth=depth)

                self.assertEqual([name for name, _ in sources], [f"com.example.{name}" for name in expected_names])
                self.assertEqual(
                    [call.args[0] for call in fetch.call_args_list],
                    [f"com/example/{name}" for name in expected_names],
                )

    def test_transitive_local_source_and_failed_dependency_do_not_block_siblings(self):
        config = Config("https", "domain.com", "1.0", "user", "pass")
        with tempfile.TemporaryDirectory() as folder:
            source_root = Path(folder) / "src" / "main" / "java" / "com" / "example"
            source_root.mkdir(parents=True)
            (source_root / "Root.java").write_text(
                "import com.example.Remote;\nimport com.example.Local;", encoding="utf-8"
            )
            (source_root / "Local.java").write_text(
                "import com.example.Child;", encoding="utf-8"
            )
            (source_root / "Child.java").write_text("class Child {}", encoding="utf-8")

            def remote_source(path, config, timeout):
                if path == "com/example/Missing":
                    raise ConfigError("not found")
                self.assertEqual(path, "com/example/Remote")
                return "import com.example.Missing;\nclass Remote {}"

            with (
                patch("fetch_resource.fetch_resource", side_effect=remote_source) as fetch,
                redirect_stderr(io.StringIO()) as warnings,
            ):
                sources = fetch_class_sources("com.example.Root", config, source_folder=folder, depth=2)

        self.assertEqual(
            [name for name, _ in sources],
            ["com.example.Root", "com.example.Remote", "com.example.Local", "com.example.Child"],
        )
        self.assertEqual(
            [call.args[0] for call in fetch.call_args_list],
            ["com/example/Remote", "com/example/Missing"],
        )
        self.assertIn("Warning: could not fetch dependency com.example.Missing", warnings.getvalue())

    def test_rejects_nonpositive_or_noninteger_programmatic_depth(self):
        config = Config("https", "domain.com", "1.0", "user", "pass")
        for depth in (0, -1, 1.5, True):
            with self.subTest(depth=depth), self.assertRaises(ConfigError):
                fetch_class_sources("com.example.Root", config, depth=depth)


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


class CliTests(unittest.TestCase):
    def test_prompts_for_password_and_uses_entered_value(self):
        environment = {
            "RESOURCE_DOMAIN": "domain.com",
            "RESOURCE_VERSION": "1.0",
            "RESOURCE_USERNAME": "user",
            "RESOURCE_PASSWORD": "environment-password",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch("fetch_resource.getpass.getpass", return_value="entered-password") as prompt,
            patch("fetch_resource.fetch_class_sources", return_value=[("com.example.Example", "")]) as fetch,
            patch("fetch_resource.write_sources_text"),
        ):
            self.assertEqual(main(["com.example.Example"]), 0)

        prompt.assert_called_once_with("Password: ")
        self.assertEqual(fetch.call_args.args[1].password, "entered-password")
        self.assertEqual(fetch.call_args.args[-1], 1)

    def test_explicit_depth_reaches_fetcher(self):
        environment = {
            "RESOURCE_DOMAIN": "domain.com",
            "RESOURCE_VERSION": "1.0",
            "RESOURCE_USERNAME": "user",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch("fetch_resource.getpass.getpass", return_value="password"),
            patch("fetch_resource.fetch_class_sources", return_value=[]) as fetch,
            patch("fetch_resource.write_sources_text"),
        ):
            self.assertEqual(main(["com.example.Root", "--depth", "3"]), 0)

        self.assertEqual(fetch.call_args.args[-1], 3)

    def test_rejects_invalid_depth_before_prompt(self):
        for depth in ("0", "-1", "abc"):
            with (
                self.subTest(depth=depth),
                patch("fetch_resource.getpass.getpass") as prompt,
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as exit_status,
            ):
                main(["com.example.Root", "--depth", depth])

            self.assertEqual(exit_status.exception.code, 2)
            prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
