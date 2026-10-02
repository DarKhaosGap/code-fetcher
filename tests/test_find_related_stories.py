from contextlib import redirect_stdout
from io import StringIO
import sys
import types
import unittest
from unittest.mock import Mock, patch

try:
    import requests  # noqa: F401
except ModuleNotFoundError:
    requests_stub = types.ModuleType("requests")
    requests_stub.RequestException = Exception
    requests_stub.HTTPError = Exception
    requests_stub.post = None
    auth_stub = types.ModuleType("requests.auth")
    auth_stub.HTTPBasicAuth = object
    requests_stub.auth = auth_stub
    sys.modules["requests"] = requests_stub
    sys.modules["requests.auth"] = auth_stub
else:
    if not hasattr(requests, "post"):
        requests.post = None

from find_related_stories import JiraConfig, count_related_stories, issue_matches, main


class IssueMatchingTests(unittest.TestCase):
    def test_matches_any_keyword_case_insensitively_in_summary(self):
        issue = {"fields": {"summary": "Improve Search", "description": None}}
        self.assertTrue(issue_matches(issue, ["billing", "SEARCH"]))

    def test_matches_keyword_in_atlassian_document_format_description(self):
        issue = {
            "fields": {
                "summary": "Feature request",
                "description": {
                    "type": "doc",
                    "content": [{"type": "paragraph", "content": [{"text": "Export CSV"}]}],
                },
            }
        }
        self.assertTrue(issue_matches(issue, ["csv"]))

    def test_does_not_match_unrelated_issue(self):
        issue = {"fields": {"summary": "Update footer", "description": "Fix spacing"}}
        self.assertFalse(issue_matches(issue, ["billing", "search"]))


class JiraPaginationTests(unittest.TestCase):
    def test_returns_unique_matching_keys_across_all_pages(self):
        config = JiraConfig("https://jira.example.com", "user@example.com", "secret")
        first_page = Mock()
        first_page.json.return_value = {
            "issues": [
                {"key": "APP-1", "fields": {"summary": "Search improvements", "description": None}},
                {"key": "APP-2", "fields": {"summary": "Unrelated", "description": ""}},
            ],
            "nextPageToken": "page-two",
            "isLast": False,
        }
        second_page = Mock()
        second_page.json.return_value = {
            "issues": [
                {"key": "APP-1", "fields": {"summary": "Search improvements", "description": None}},
                {"key": "APP-3", "fields": {"summary": "Billing export", "description": None}},
            ],
            "isLast": True,
        }

        with patch("find_related_stories.requests.post", side_effect=[first_page, second_page]) as post:
            ticket_keys = count_related_stories(config, ["APP"], ["search", "billing"])

        self.assertEqual(ticket_keys, ["APP-1", "APP-3"])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].kwargs["json"]["jql"], 'project in ("APP") AND issuetype = Story')
        self.assertEqual(post.call_args_list[1].kwargs["json"]["nextPageToken"], "page-two")
        self.assertEqual(post.call_args_list[0].kwargs["auth"], ("user@example.com", "secret"))


class CliTests(unittest.TestCase):
    def test_prints_ticket_keys_and_total(self):
        output = StringIO()
        with (
            patch("find_related_stories.load_config", return_value=JiraConfig("https://jira.example.com", "user", "token")),
            patch("find_related_stories.count_related_stories", return_value=["APP-1", "APP-3"]),
            redirect_stdout(output),
        ):
            status = main(["search", "--project", "APP"])

        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "APP-1\nAPP-3\nTotal: 2\n")


if __name__ == "__main__":
    unittest.main()