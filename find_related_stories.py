#!/usr/bin/env python3
"""List Jira Cloud story keys whose summary or description matches any keyword."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import requests

DEFAULT_TIMEOUT = 30.0
PAGE_SIZE = 100


class ConfigError(ValueError):
    """Raised when Jira connection settings or search inputs are invalid."""


@dataclass(frozen=True)
class JiraConfig:
    base_url: str
    email: str
    api_token: str


def load_config() -> JiraConfig:
    """Load Jira Cloud connection settings from environment variables."""
    values = {
        "JIRA_BASE_URL": os.getenv("JIRA_BASE_URL", "").strip().rstrip("/"),
        "JIRA_EMAIL": os.getenv("JIRA_EMAIL", "").strip(),
        "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", "").strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigError("Missing required environment variables: " + ", ".join(missing))
    if not values["JIRA_BASE_URL"].startswith(("https://", "http://")):
        raise ConfigError("JIRA_BASE_URL must be an absolute HTTP(S) URL.")
    return JiraConfig(
        base_url=values["JIRA_BASE_URL"],
        email=values["JIRA_EMAIL"],
        api_token=values["JIRA_API_TOKEN"],
    )


def _plain_text(value: object) -> str:
    """Flatten Jira's plain-string or Atlassian Document Format field values."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_plain_text(item) for item in value)
    if isinstance(value, dict):
        own_text = value.get("text", "")
        nested_text = " ".join(
            _plain_text(child) for child in value.values() if isinstance(child, (dict, list))
        )
        return f"{own_text} {nested_text}".strip()
    return ""


def issue_matches(issue: dict, keywords: list[str]) -> bool:
    """Return whether any keyword occurs in an issue's summary or description."""
    fields = issue.get("fields", {})
    content = f"{_plain_text(fields.get('summary'))} {_plain_text(fields.get('description'))}".casefold()
    return any(keyword.casefold() in content for keyword in keywords)


def count_related_stories(
    config: JiraConfig,
    projects: list[str],
    keywords: list[str],
    timeout: float = DEFAULT_TIMEOUT,
) -> list[str]:
    """Return unique keys for Story issues matching any keyword in selected projects."""
    projects = [project.strip() for project in projects if project.strip()]
    keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
    if not projects:
        raise ConfigError("Provide at least one Jira project key.")
    if not keywords:
        raise ConfigError("Provide at least one non-empty keyword.")

    project_values = ", ".join(
        '"' + project.replace("\\", "\\\\").replace('"', '\\"') + '"'
        for project in projects
    )
    jql = f"project in ({project_values}) AND issuetype = Story"
    url = f"{config.base_url}/rest/api/3/search/jql"
    next_page_token = None
    seen_tokens: set[str] = set()
    seen_issues: set[str] = set()
    matching_keys: list[str] = []

    while True:
        payload = {
            "jql": jql,
            "fields": ["summary", "description"],
            "maxResults": PAGE_SIZE,
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token

        response = requests.post(
            url,
            json=payload,
            auth=(config.email, config.api_token),
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()

        for issue in result.get("issues", []):
            issue_key = issue.get("key")
            if not issue_key or issue_key in seen_issues:
                continue
            seen_issues.add(issue_key)
            if issue_matches(issue, keywords):
                matching_keys.append(issue_key)

        next_page_token = result.get("nextPageToken")
        if not next_page_token or result.get("isLast", False):
            break
        if next_page_token in seen_tokens:
            raise RuntimeError("Jira returned a repeated pagination token.")
        seen_tokens.add(next_page_token)

    return matching_keys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List Jira Story ticket keys matching any supplied keyword."
    )
    parser.add_argument(
        "keywords",
        nargs="+",
        help="Keywords to match in story summaries or descriptions",
    )
    parser.add_argument(
        "--project",
        action="append",
        required=True,
        help="Jira project key; pass this option more than once for multiple projects",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config()
        ticket_keys = count_related_stories(config, args.project, args.keywords, args.timeout)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        print(f"Jira request failed with HTTP status {status}.", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Jira request failed: {exc.__class__.__name__}.", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Jira response error: {exc}.", file=sys.stderr)
        return 1

    for ticket_key in ticket_keys:
        print(ticket_key)
    print(f"Total: {len(ticket_keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())