#!/usr/bin/env python3
"""Fetch a versioned remote resource over HTTP(S) using basic authentication."""

from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_PROTOCOL = "https"
DEFAULT_TIMEOUT = 30.0
ALLOWED_PROTOCOLS = ("http", "https")
JAVA_IMPORT_PATTERN = re.compile(
    r"^\s*import\s+(?P<static>static\s+)?"
    r"(?P<name>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)"
    r"(?P<wildcard>\.\*)?\s*;",
    re.MULTILINE,
)
STANDARD_LIBRARY_PREFIXES = ("java.", "javax.", "sun.", "com.sun.")


class ConfigError(ValueError):
    """Raised when the required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    protocol: str
    domain: str
    version: str
    username: str
    password: str


def load_config(
    protocol: str | None = None,
    domain: str | None = None,
    version: str | None = None,
) -> Config:
    """Build the configuration from environment variables and optional overrides."""
    resolved = {
        "protocol": (protocol or os.getenv("RESOURCE_PROTOCOL") or DEFAULT_PROTOCOL).lower(),
        "domain": domain or os.getenv("RESOURCE_DOMAIN", ""),
        "version": version or os.getenv("RESOURCE_VERSION", ""),
        "username": os.getenv("RESOURCE_USERNAME", ""),
        "password": os.getenv("RESOURCE_PASSWORD", ""),
    }

    missing = [name for name, value in resolved.items() if not value.strip()]
    if missing:
        raise ConfigError(
            "Missing required configuration: "
            + ", ".join(f"RESOURCE_{name.upper()}" for name in missing)
        )

    if resolved["protocol"] not in ALLOWED_PROTOCOLS:
        raise ConfigError(
            f"Unsupported protocol {resolved['protocol']!r}; expected one of {ALLOWED_PROTOCOLS}."
        )

    return Config(**{key: value.strip() for key, value in resolved.items()})


def build_url(config: Config, resource_path: str) -> str:
    """Compose protocol, domain, version and resource path into an absolute URL."""
    domain = config.domain.strip()
    try:
        parsed_domain = urlsplit(f"//{domain}")
        hostname = parsed_domain.hostname
    except ValueError as exc:
        raise ConfigError(f"Invalid domain {config.domain!r}; expected a valid host.") from exc
    if (
        not hostname
        or parsed_domain.username is not None
        or parsed_domain.password is not None
        or parsed_domain.query
        or parsed_domain.fragment
        or "\\" in domain
    ):
        raise ConfigError(
            f"Invalid domain {config.domain!r}; expected a host with an optional base path."
        )

    try:
        parsed_domain.port
    except ValueError as exc:
        raise ConfigError(f"Invalid domain {config.domain!r}; port is not valid.") from exc

    raw_base_segments = parsed_domain.path.split("/")
    interior_segments = raw_base_segments[1:-1]
    if (
        any(not segment for segment in interior_segments)
        or any(unquote(segment) in (".", "..") for segment in raw_base_segments if segment)
    ):
        raise ConfigError(f"Invalid domain {config.domain!r}; base path contains an unsafe segment.")
    base_segments = [segment for segment in raw_base_segments if segment]

    resource_path = resource_path.strip().rstrip("/")
    if not resource_path or not any(resource_path.split("/")):
        raise ConfigError("Resource path must contain at least one segment.")
    if not resource_path.endswith(".java"):
        resource_path += ".java"

    # Percent-encode each segment so the caller cannot alter the host, query or fragment.
    segments = [
        quote(segment, safe="")
        for segment in (*base_segments, config.version, *resource_path.split("/"))
        if segment
    ]

    return f"{config.protocol}://{parsed_domain.netloc}/" + "/".join(segments)


def class_name_to_resource_path(class_name: str) -> str:
    """Convert a dotted Java class name into a slash-separated resource path."""
    value = class_name.strip()
    if not value or "/" in value or "\\" in value:
        raise ConfigError("Class name must be a dotted name without path separators.")

    extension = ".java" if value.endswith(".java") else ""
    base_name = value[: -len(extension)] if extension else value
    segments = base_name.split(".")
    if len(segments) < 2 or any(not segment for segment in segments):
        raise ConfigError("Class name must include a package and class name.")

    return "/".join(segments) + extension


def extract_imports(source: str) -> list[str]:
    """Return explicit non-platform Java class imports from source text."""
    dependencies: list[str] = []
    for match in JAVA_IMPORT_PATTERN.finditer(source):
        if match.group("wildcard"):
            continue

        imported_name = match.group("name")
        if match.group("static"):
            imported_name = imported_name.rsplit(".", 1)[0]
        if imported_name.startswith(STANDARD_LIBRARY_PREFIXES) or imported_name in dependencies:
            continue
        dependencies.append(imported_name)
    return dependencies


def fetch_class_sources(
    class_name: str,
    config: Config,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[tuple[str, str]]:
    """Fetch a class and its direct project dependencies."""
    sources = [(class_name, fetch_resource(class_name_to_resource_path(class_name), config, timeout))]
    fetched_names = {class_name}

    for dependency_name in extract_imports(sources[0][1]):
        if dependency_name in fetched_names:
            continue
        fetched_names.add(dependency_name)
        try:
            dependency_body = fetch_resource(
                class_name_to_resource_path(dependency_name), config, timeout
            )
        except (ConfigError, requests.RequestException) as exc:
            print(f"Warning: could not fetch dependency {dependency_name}: {exc}", file=sys.stderr)
            continue
        sources.append((dependency_name, dependency_body))

    return sources


def format_class_sources(sources: list[tuple[str, str]]) -> str:
    """Format fetched class bodies with fully qualified class-name headers."""
    return "\n\n".join(f"===== {class_name} =====\n{body}" for class_name, body in sources)


def class_name_to_filename(class_name: str) -> str:
    """Convert a fully qualified class name into a simple Java source filename."""
    base_name = class_name.removesuffix(".java")
    simple_name = base_name.rsplit(".", 1)[-1]
    return f"{simple_name}.java"


def write_sources_zip(sources: list[tuple[str, str]], output_path: str) -> None:
    """Write fetched class sources to a ZIP archive using simple class filenames."""
    filenames = [class_name_to_filename(class_name) for class_name, _ in sources]
    duplicates = {name for name in filenames if filenames.count(name) > 1}
    if duplicates:
        raise ConfigError(
            "Duplicate class filenames: " + ", ".join(sorted(duplicates))
        )

    try:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename, (_, body) in zip(filenames, sources):
                archive.writestr(filename, body)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ConfigError(f"Could not write output ZIP {output_path!r}: {exc}") from exc


def fetch_resource(
    resource_path: str,
    config: Config,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Perform the authenticated GET request and return the response body as text."""
    url = build_url(config, resource_path)
    response = requests.get(
        url,
        auth=HTTPBasicAuth(config.username, config.password),
        timeout=timeout,
    )
    response.raise_for_status()

    if response.encoding is None:
        response.encoding = "utf-8"
    return response.text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a versioned resource using basic authentication. Protocol, domain, version "
            "and credentials are read from the RESOURCE_PROTOCOL, RESOURCE_DOMAIN, "
            "RESOURCE_VERSION, RESOURCE_USERNAME and RESOURCE_PASSWORD environment variables."
        )
    )
    parser.add_argument(
        "class_name",
        help="Fully qualified class name to fetch, e.g. com.example.Example",
    )
    parser.add_argument(
        "-v",
        "--version",
        dest="version",
        help="Override RESOURCE_VERSION, e.g. 27.1.0",
    )
    parser.add_argument("--protocol", help=f"Override RESOURCE_PROTOCOL (default: {DEFAULT_PROTOCOL})")
    parser.add_argument("--domain", help="Override RESOURCE_DOMAIN")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--output",
        default="dependencies.zip",
        help="Output ZIP path (default: dependencies.zip)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.protocol, args.domain, args.version)
        sources = fetch_class_sources(args.class_name, config, args.timeout)
        write_sources_zip(sources, args.output)
        print(f"Wrote {len(sources)} class source(s) to {args.output}")
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        print(f"Request failed with HTTP status {status}.", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Request failed: {exc.__class__.__name__}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
