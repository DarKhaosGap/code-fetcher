#!/usr/bin/env python3
"""Fetch a versioned remote resource over HTTP(S) using basic authentication."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_PROTOCOL = "https"
DEFAULT_TIMEOUT = 30.0
ALLOWED_PROTOCOLS = ("http", "https")


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
    domain = config.domain.strip().strip("/")
    if "/" in domain or "@" in domain:
        raise ConfigError(f"Invalid domain {config.domain!r}; expected a host name only.")

    # Percent-encode each segment so the caller cannot alter the host, query or fragment.
    segments = [
        quote(segment, safe="")
        for segment in (config.version, *resource_path.split("/"))
        if segment
    ]
    if not segments[1:]:
        raise ConfigError("Resource path must contain at least one segment.")

    return f"{config.protocol}://{domain}/" + "/".join(segments)


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
        "resource_path",
        help="Resource path to fetch, e.g. /com/example/Example.java",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.protocol, args.domain, args.version)
        body = fetch_resource(args.resource_path, config, args.timeout)
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

    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
