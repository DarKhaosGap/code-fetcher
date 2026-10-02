# Count Related Jira Stories

## Summary
Add a standalone CLI named `find_related_stories.py` that finds Jira Cloud stories related to supplied keywords and returns their ticket identifiers.

## Requirements
- Accept one or more keywords and one or more Jira project keys.
- Search Jira issue type `Story` in the selected projects; match any keyword case-insensitively in summary or description.
- Return each matching issue's ticket key once, fetch all result pages, and use Jira Cloud basic authentication without exposing the API token in arguments.
- Print all matching ticket keys and their total count.

## Scope
- `find_related_stories.py`: Jira Cloud API client, keyword matching, pagination, and CLI.
- `tests/test_find_related_stories.py`: focused tests for matching and pagination.
- `README.md`: configuration and invocation instructions.

## Implementation
`find_related_stories.py` reads `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN`; accepts repeated `--project` arguments and positional keywords; queries Jira's `/rest/api/3/search/jql` endpoint for `Story` issues; flattens plain-text and Atlassian Document Format descriptions; and returns unique matching issue keys. The CLI prints the keys and their total. `README.md` documents configuration and usage. The renamed tests mock paginated responses and cover matching behavior, ADF descriptions, and duplicate issue keys.

## Validation
- `python -m unittest tests.test_find_related_stories -v` passed with four tests before ticket-key output was added.
- `python -m unittest discover -s tests -v` passed with all twelve repository tests.
- `python -m unittest tests.test_find_related_stories -v` passed with five tests after the rename.
- `python -m py_compile find_related_stories.py tests/test_find_related_stories.py` passed after the rename.
- `python -m unittest discover -s tests -v` passed with all thirteen tests after the rename; `git diff --check HEAD` passed.
- After adding ticket-key output, focused Jira tests passed with five tests, full test discovery passed all thirteen tests, and Python compilation passed; these checks will be rerun after the rename.
- No live Jira request was made; connection settings and API access remain to be verified in the user's environment.

## Status
Complete. The script returns every unique matching Jira ticket key, prints one key per line, and prints the total. It requires the `requests` dependency from `requirements.txt` and valid Jira Cloud credentials with access to the projects.
