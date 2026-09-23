# Fetch Resource Script

## Summary
Provide a Python CLI that fetches a Java class and its direct project dependencies from a versioned
repository-style endpoint, optionally preferring matching sources from a local project folder, then
writes the successful responses to a text file.

## Requirements
- Compose URLs from a protocol, domain, version, and a full dotted class name.
- Allow the domain to include a safe base path, such as `domain.com/other`, before the version
  and class resource path.
- Read protocol, domain, version, and credentials from environment variables, with CLI overrides for
  protocol, domain, version, timeout, and output path.
- Convert `com.example.Example` to `com/example/Example` and preserve a terminal `.java` suffix.
- Ensure every requested resource URL ends with `.java`, adding the suffix when the resource path
  does not already include it.
- Reject empty class-name segments and slash-separated input.
- Fetch the requested class and each unique direct project import once; do not recurse into
  transitive dependencies.
- When a source folder is provided, resolve the requested class and direct dependencies from Java
  files beneath that folder before falling back to the existing remote fetch behavior.
- Support project roots containing Java source layouts such as `src/main/java/com/example/Example.java`.
- Include explicit ordinary and static imports, while skipping wildcard and standard-library
  packages such as `java.*`, `javax.*`, `sun.*`, and `com.sun.*`.
- Continue with a warning when a dependency cannot be fetched; a root-class failure remains fatal.
- Write successful responses to one UTF-8 text file with fully qualified class-name headers.
- Use HTTP basic authentication and an explicit request timeout.
- Return non-zero status with a message on stderr for configuration, root request, or output
  errors. Never log or echo credentials.

## Scope
- `fetch_resource.py`: CLI entry point, configuration, URL construction, dependency discovery,
  local source lookup, HTTP fetching, and text output.
- `tests/test_fetch_resource.py`: unit tests for domain URL composition, validation, and local-first
  source resolution with remote fallback.
- `requirements.txt`: declares the `requests` dependency.
- `README.md`: documents environment setup and command-line usage.

## Implementation
- `load_config()` resolves `RESOURCE_PROTOCOL`, `RESOURCE_DOMAIN`, `RESOURCE_VERSION`,
  `RESOURCE_USERNAME`, and `RESOURCE_PASSWORD`, defaulting the protocol to `https`.
- `class_name_to_resource_path()` validates dotted class names and converts them to slash-separated
  resource paths.
- `build_url()` quotes each URL path segment and accepts only `http` and `https` protocols.
- `build_url()` accepts a host with optional base-path segments, while rejecting credentials,
  queries, fragments, empty segments, and `..` traversal segments.
- `build_url()` normalizes the final resource path segment to end in `.java` before URL encoding.
- `extract_imports()` parses explicit Java imports, resolves static imports to their owning class,
  removes duplicates, and filters wildcard/platform imports.
- `read_local_class_source()` searches the supplied project folder recursively for a path matching
  the class package and filename, reads a unique UTF-8 match, and rejects ambiguous matches.
- `fetch_class_sources()` resolves the root class followed by its direct dependencies from local
  sources first, falling back to remote requests for classes not found locally. Dependency lookup
  failures are reported as warnings and skipped.
- `format_class_sources()` combines source bodies with fully qualified class-name headers.
- `write_sources_text()` writes the combined source text with UTF-8 encoding and reports filesystem
  errors through `ConfigError`.
- `argparse` accepts the class name as a positional argument, `--source-folder` as the optional
  local project root, and `--output` defaults to `dependencies.txt`.
- The CLI reports the number of written class sources and the output path on stdout.

## Validation
- `python -m py_compile fetch_resource.py` passed.
- Isolated dependency checks passed for import filtering, static imports, deduplication, direct
  fetch ordering, and tagged-output behavior before archive output was introduced.
- Text output checks passed for class-name headers, multiple source bodies, and UTF-8 content.
- Unit tests cover plain-host and base-path URL composition plus unsafe-domain rejection.
- Unit tests cover adding `.java` to extensionless resource paths and preserving an existing suffix.
- `python -m unittest discover -s tests -v` passed with six tests.
- Unit tests verify recursive local lookup beneath `src/main/java`, local dependency loading, and
  remote fallback only for a dependency absent from the supplied folder.
- `git diff --check` passed.
- CLI help could not be executed because `requests` was not installed in the validation environment.
- No real network call was executed.

## Status
Complete. Optional local-first source resolution, remote fallback, and combined text output are
implemented and documented.
Retries, backoff, recursive dependency traversal, wildcard resolution, and proxy configuration are
out of scope.
