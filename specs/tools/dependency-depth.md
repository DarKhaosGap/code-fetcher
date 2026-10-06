# Configurable Dependency Depth

## Summary
Allow callers to choose how many levels of Java import dependencies to fetch while preserving the current direct-import default.

## Requirements
- Accept a positive integer depth, defaulting to 1. Depth 1 includes direct imports; depth 2 also includes imports of those classes.
- Reject zero, negative, and non-integer CLI depth values.
- Keep local-first resolution, import filtering, deduplication, warnings on failed dependencies, and root-first output.

## Scope
- `fetch_resource.py`: bounded dependency traversal, programmatic depth validation, and `--depth` CLI option.
- `tests/test_fetch_resource.py`: traversal, local/remote fallback, failure handling, and CLI regression tests.
- `README.md`: CLI usage and depth examples.
- `specs/tools/dependency-depth.md`: this change record.

## Implementation
Traverse successfully loaded sources breadth-first, stopping before imports beyond the requested depth. Shared and cyclic imports are fetched once. Pass `--depth` through to the fetcher and validate positive integers both at the CLI and for direct callers. Failed dependencies are warned about and not expanded.

## Validation
- `python -m unittest discover -s tests -p test_fetch_resource.py -v`: 13 tests passed.
- `python -m unittest discover -s tests -v`: 18 tests passed.
- `python -m py_compile fetch_resource.py` and `git diff --check` passed.
- `python fetch_resource.py --help` could not run because `requests` is not installed in this environment; CLI behavior is covered by unit tests with the existing requests stub. No live network request was made.

## Status
Complete. Depth must be a positive integer; depth 1 preserves direct-import behavior. Wildcard import resolution remains out of scope.