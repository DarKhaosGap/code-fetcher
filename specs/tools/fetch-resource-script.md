# Fetch Resource Script

## Summary
Provide a Python CLI that fetches a Java class and its direct project dependencies from a versioned
repository-style endpoint, then writes the successful responses to a ZIP archive.

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
- Include explicit ordinary and static imports, while skipping wildcard and standard-library
  packages such as `java.*`, `javax.*`, `sun.*`, and `com.sun.*`.
- Continue with a warning when a dependency cannot be fetched; a root-class failure remains fatal.
- Write successful responses to a ZIP archive. Use simple class filenames without packages and
  always use the `.java` extension.
- Reject duplicate simple filenames instead of overwriting entries.
- Use HTTP basic authentication and an explicit request timeout.
- Return non-zero status with a message on stderr for configuration, root request, or archive
  errors. Never log or echo credentials.

## Scope
- `fetch_resource.py`: CLI entry point, configuration, URL construction, dependency discovery,
  HTTP fetching, and ZIP archive output.
- `tests/test_fetch_resource.py`: unit tests for domain URL composition and validation.
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
- `fetch_class_sources()` fetches the root class followed by its direct dependencies. Dependency
  request failures are reported as warnings and skipped.
- `class_name_to_filename()` removes packages and normalizes each class to a `.java` filename.
- `write_sources_zip()` writes UTF-8 response bodies with `zipfile`, detects duplicate filenames,
  and reports filesystem/archive errors through `ConfigError`.
- `argparse` accepts the class name as a positional argument and `--output` defaults to
  `dependencies.zip`.
- The CLI reports the number of archived class sources and the output path on stdout.

## Validation
- `python -m py_compile fetch_resource.py` passed.
- Isolated dependency checks passed for import filtering, static imports, deduplication, direct
  fetch ordering, and tagged-output behavior before archive output was introduced.
- ZIP checks passed for simple-name conversion, `.java` normalization, UTF-8 content, and duplicate
  filename rejection.
- Unit tests cover plain-host and base-path URL composition plus unsafe-domain rejection.
- Unit tests cover adding `.java` to extensionless resource paths and preserving an existing suffix.
- `.venv\Scripts\python.exe -m unittest discover -s tests -v` passed with five tests.
- `git diff --check` passed.
- CLI help could not be executed because `requests` was not installed in the validation environment.
- No real network call was executed.

## Status
Complete. Direct dependency fetching, warning behavior, ZIP archive output, and README usage
documentation are implemented.
Retries, backoff, recursive dependency traversal, wildcard resolution, and proxy configuration are
out of scope.
